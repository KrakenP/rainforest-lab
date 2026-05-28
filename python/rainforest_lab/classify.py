from __future__ import annotations

from typing import Any

from rainforest_lab.state import Classification, GateDef, GateRecord


def classify(rec: GateRecord, spec: list[GateDef]) -> tuple[Classification, str]:
    sick_reason = _sick_reason(rec)
    if sick_reason:
        return "sick_leaf", f"{sick_reason}; blocked_from_reuse"

    complete = rec.is_complete(spec)
    hard_gates = [gate_def for gate_def in spec if gate_def.hard]
    hard_passes = [_gate_passed(rec.gates.get(gate_def.name, {})) for gate_def in hard_gates]
    all_hard_pass = bool(hard_gates) and all(hard_passes)
    g7_score = _g7_score(rec)

    if complete and all_hard_pass and g7_score >= 1:
        if rec.execution_mode != "tool_executed":
            raise ValueError("fruit requires execution_mode='tool_executed'")
        if g7_score >= 2:
            return "fruit", "all hard gates pass; G7>=2 promoted fruit"
        return "fruit", "all hard gates pass; G7>=1 ensemble fruit"

    if _boundary_informative(rec, hard_passes):
        return "golden_leaf", "hard gate failed but boundary-informative with sanity support"

    if _weak_everywhere(rec, hard_passes):
        return "dead_leaf", "weak everywhere; no hard-gate support or boundary information"

    return "normal_leaf", "partial or incomplete evidence without hard failure signal"


def _gate_passed(gate: dict[str, Any]) -> bool:
    value = gate.get("passed")
    if isinstance(value, bool):
        return value
    score = gate.get("score")
    if isinstance(score, int | float):
        return score > 0
    return False


def _g7_score(rec: GateRecord) -> float:
    gate = rec.gates.get("G7") or rec.gates.get("g7") or {}
    score = gate.get("score")
    if isinstance(score, int | float):
        return float(score)
    passed = gate.get("passed")
    if isinstance(passed, bool):
        return 1.0 if passed else 0.0
    return 0.0


def _sick_reason(rec: GateRecord) -> str:
    for gate_name, gate in rec.gates.items():
        for key in ("lookahead", "leakage", "invalid_data"):
            if bool(gate.get(key)):
                return f"{gate_name} flagged {key}"
        status = str(gate.get("status", "")).lower()
        if status in {"lookahead", "leakage", "invalid_data", "sick"}:
            return f"{gate_name} flagged {status}"
    return ""


def _boundary_informative(rec: GateRecord, hard_passes: list[bool]) -> bool:
    if any(bool(gate.get("boundary_informative")) for gate in rec.gates.values()):
        return True
    if any(bool(gate.get("sub_regime")) for gate in rec.gates.values()):
        return True
    if any(bool(gate.get("weak_signal")) for gate in rec.gates.values()) and any(hard_passes):
        return True
    sanity_gate = rec.gates.get("sanity") or rec.gates.get("G3") or rec.gates.get("g3") or {}
    return any(hard_passes) and _gate_passed(sanity_gate)


def _weak_everywhere(rec: GateRecord, hard_passes: list[bool]) -> bool:
    if any(hard_passes):
        return False
    for gate in rec.gates.values():
        score = gate.get("score")
        if isinstance(score, int | float) and score > 0:
            return False
        if bool(gate.get("passed")):
            return False
    return True


__all__ = ["classify"]
