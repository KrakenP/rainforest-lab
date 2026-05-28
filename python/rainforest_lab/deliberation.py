"""Bounded per-tree deliberation round (rainforest v2.0).

Pure orchestration over the rainforest LLM Protocols: a gardener mines hypotheses, an adversarial
(different-model) skeptic critiques them across bounded debate rounds, survivors flow through the
v1 pipeline (divergence → inspector → nursery → examiner → G7 → classify), and each fruit-candidate
gets a recorded (non-vetoing) skeptic second challenge before G7.

This module NEVER mutates forest state — it reads the forest and returns a `TreeDeliberation`
bundle. The coordinator (`cycle.py`) is the sole writer and merges per-tree bundles in a
deterministic, tree_id-sorted order so the cycle stays reproducible.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, cast

from rainforest_lab import events, seeds
from rainforest_lab.classify import classify as classify_record
from rainforest_lab.domain import ResearchDomain
from rainforest_lab.llm.protocols import SEVERITY_ORDER, Judgment, Mechanism
from rainforest_lab.roles import role
from rainforest_lab.state import GateDef, GateRecord, ResultRecord, Seed, Tree

DEFAULT_HANDOFF_TIMEOUT_S = 1800

_DIVERGENCE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "formula": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["formula"],
                "additionalProperties": True,
            },
        }
    },
    "additionalProperties": True,
}


@dataclass(frozen=True)
class DeliberationConfig:
    """Knobs for the per-tree debate. `max_debate_rounds=0` runs no debate (v1-equivalent)."""

    max_debate_rounds: int = 0
    cull_severity: str = "high"
    skeptic_model: str = "deepseek"
    gardener_model: str = "kimi"


@dataclass(frozen=True)
class ParallelGardenersConfig:
    """How the coordinator fans gardeners across allocated trees."""

    max_concurrent: int = 1
    temperature_spread: tuple[float, ...] = (1.0,)


@dataclass
class TreeDeliberation:
    """Pure result of one tree's deliberation; the coordinator merges these deterministically."""

    tree_id: str
    seeds: list[Seed] = field(default_factory=list)
    records: list[tuple[dict[str, Any], ResultRecord]] = field(default_factory=list)


def deliberate_tree(
    tree: Tree,
    forest: Any,
    domain: ResearchDomain,
    *,
    temperature: float,
    config: DeliberationConfig,
    gardener: Any,
    skeptic: Any,
    deepseek: Any,
    handoff: Any,
    events_path: Path,
    cycle: int,
    promoted_pool: dict[str, Any],
) -> TreeDeliberation:
    """Run a bounded gardener↔skeptic deliberation for one tree and return candidate data.

    Side-effect free w.r.t. `forest`: reads taboos/explored/climate, returns a `TreeDeliberation`.
    """

    td = TreeDeliberation(tree_id=tree.tree_id)
    feature_space = domain.feature_space()
    taboos = _taboos(forest)
    explored = _explored(forest)
    n = max(1, forest.climate.seed_slots)

    base_logic = tree.core_logic or forest.research_goal
    mined = gardener.mine(
        _styled_logic(base_logic, temperature), feature_space, taboos, explored, n
    )
    _emit(
        events_path,
        "gardener",
        "mine",
        tree.tree_id,
        {"tree_id": tree.tree_id, "temperature": temperature, "n": n},
        {"mechanisms": [_public_dict(m) for m in mined]},
        "gardener mined hypotheses for this tree before adversarial debate.",
        cycle,
    )

    survivors = _debate(
        mined,
        tree,
        domain,
        config=config,
        gardener=gardener,
        skeptic=skeptic,
        feature_space=feature_space,
        taboos=taboos,
        explored=explored,
        events_path=events_path,
        cycle=cycle,
    )

    divergent = _request_divergence(survivors, tree, forest, handoff, events_path, cycle)

    td.seeds = _build_seeds(survivors, divergent, tree, forest, deepseek, events_path, cycle)
    td.seeds = seeds.rank_and_route(td.seeds, slots=forest.climate.seed_slots)

    tasks = _build_tasks(td.seeds, tree, forest, events_path, cycle)
    gate_spec = domain.gate_spec()
    for task in tasks:
        record = _evaluate_task(
            task,
            domain,
            gate_spec,
            config=config,
            skeptic=skeptic,
            handoff=handoff,
            events_path=events_path,
            cycle=cycle,
            promoted_pool=promoted_pool,
        )
        td.records.append((task, record))

    return td


def _debate(
    mined: list[Mechanism],
    tree: Tree,
    domain: ResearchDomain,
    *,
    config: DeliberationConfig,
    gardener: Any,
    skeptic: Any,
    feature_space: Any,
    taboos: list[str],
    explored: list[str],
    events_path: Path,
    cycle: int,
) -> list[Mechanism]:
    if config.max_debate_rounds <= 0:
        return list(mined)

    cull_bar = SEVERITY_ORDER.get(config.cull_severity, SEVERITY_ORDER["high"])
    active = list(mined)
    settled: list[Mechanism] = []

    for round_idx in range(config.max_debate_rounds):
        if not active:
            break
        next_active: list[Mechanism] = []
        culled = revised = proceeded = 0
        for mechanism in active:
            verdict = skeptic.critique(
                _public_dict(mechanism),
                "hypothesis",
                gardener_model=config.gardener_model,
            )
            if verdict.verdict == "reject" and SEVERITY_ORDER[verdict.severity] >= cull_bar:
                culled += 1
                continue
            if verdict.verdict == "proceed":
                proceeded += 1
                settled.append(mechanism)
                continue
            revised += 1
            replacement = gardener.mine(
                _revision_logic(tree.core_logic, verdict),
                feature_space,
                taboos,
                explored,
                1,
            )[0]
            next_active.append(replacement)
        _emit(
            events_path,
            "skeptic",
            "debate_round",
            tree.tree_id,
            {"tree_id": tree.tree_id, "round": round_idx + 1, "in": len(active)},
            {"culled": culled, "revised": revised, "proceeded": proceeded},
            "skeptic critiqued the tree's hypotheses; gardener revised survivors this round.",
            cycle,
        )
        active = next_active

    return settled + active


def _request_divergence(
    mechanisms: list[Mechanism],
    tree: Tree,
    forest: Any,
    handoff: Any,
    events_path: Path,
    cycle: int,
) -> list[dict[str, Any]]:
    response = handoff.request(
        "divergence",
        {"mechanisms": [_public_dict(mechanism) for mechanism in mechanisms]},
        _DIVERGENCE_SCHEMA,
        req_id=f"{forest.cycle_id}-{tree.tree_id}-divergence",
        timeout_s=DEFAULT_HANDOFF_TIMEOUT_S,
    )
    candidates = response.get("candidates", [])
    if not isinstance(candidates, list):
        candidates = []
    result = [candidate for candidate in candidates if isinstance(candidate, dict)]
    _emit(
        events_path,
        "diverger",
        "handoff_divergence",
        tree.tree_id,
        {"mechanism_count": len(mechanisms)},
        {"candidate_count": len(result), "candidates": result},
        "Claude divergence handoff returned schema-bounded alternative candidates.",
        cycle,
    )
    return result


def _build_seeds(
    mechanisms: list[Mechanism],
    divergent: list[dict[str, Any]],
    tree: Tree,
    forest: Any,
    deepseek: Any,
    events_path: Path,
    cycle: int,
) -> list[Seed]:
    seeds_out: list[Seed] = []
    used_ids = {seed.seed_id for seed in forest.seeds}
    for idx, mechanism in enumerate(mechanisms, start=1):
        judgment: Judgment = deepseek.judge(mechanism)
        _emit(
            events_path,
            "inspector",
            "judge",
            mechanism.name,
            {"mechanism": _public_dict(mechanism)},
            {"judgment": _public_dict(judgment)},
            "DeepSeek inspector judged mechanism consistency, novelty, and leakage risk.",
            cycle,
        )
        seed_id = _unique_id(f"seed_{forest.cycle_id}_{tree.tree_id}_{idx}", used_ids)
        seeds_out.append(
            Seed(
                seed_id=seed_id,
                idea=mechanism.intuition,
                source_type="kimi",
                related_trees=[tree.tree_id],
                scores=_scores_from_judgment(judgment),
                status="hold",
                validation_plan=_formula_from_text(mechanism.pseudocode),
                reason=f"{mechanism.name}: {judgment.concerns}",
            )
        )
    for idx, candidate in enumerate(divergent, start=1):
        seed_id = _unique_id(f"seed_{forest.cycle_id}_{tree.tree_id}_div_{idx}", used_ids)
        formula = str(candidate.get("formula", "")).strip()
        seeds_out.append(
            Seed(
                seed_id=seed_id,
                idea=str(candidate.get("name") or candidate.get("reason") or formula),
                source_type="handoff_divergence",
                related_trees=[tree.tree_id],
                scores={
                    "novelty": 0.75,
                    "logic_strength": 0.70,
                    "option_value": 0.60,
                    "cross_tree_potential": 0.30,
                    "regime_relevance": 0.50,
                    "evidence_hint": 0.40,
                    "data_availability": 1.0,
                    "validation_cost": 0.25,
                    "leakage_risk": 0.0,
                    "redundancy": 0.10,
                },
                status="hold",
                validation_plan=_formula_from_text(formula),
                reason=str(candidate.get("reason") or "divergence handoff candidate"),
            )
        )
    return seeds_out


def _build_tasks(
    routed_seeds: list[Seed],
    tree: Tree,
    forest: Any,
    events_path: Path,
    cycle: int,
) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for seed in routed_seeds:
        if seed.status != "sow_now":
            continue
        nursery = seeds.nursery_check(seed, forest)
        _emit(
            events_path,
            "coordinator",
            "nursery_check",
            seed.seed_id,
            {"seed_id": seed.seed_id, "status": seed.status},
            {"decision": _public_dict(nursery)},
            "nursery applied seven bounded checks before candidate execution.",
            cycle,
        )
        if nursery.decision != "sprout":
            seed.status = nursery.decision  # type: ignore[assignment]
            seed.reason = nursery.reason
            seed.validation_plan = nursery.next_validation
            continue
        tasks.append(
            {
                "task_id": f"task_{forest.cycle_id}_{tree.tree_id}_{len(tasks) + 1:03d}",
                "seed_id": seed.seed_id,
                "tree_id": tree.tree_id,
                "formula": seed.validation_plan,
                "mechanism": seed.idea,
                "execution_mode": "tool_executed",
            }
        )
    return tasks


def _evaluate_task(
    task: dict[str, Any],
    domain: ResearchDomain,
    gate_spec: list[GateDef],
    *,
    config: DeliberationConfig,
    skeptic: Any,
    handoff: Any,
    events_path: Path,
    cycle: int,
    promoted_pool: dict[str, Any],
) -> ResultRecord:
    compiled = domain.compile_candidate(str(task["formula"]))
    gate_record = domain.evaluate(
        compiled, run_id=str(task["task_id"]), promoted_pool=promoted_pool
    )
    _emit(
        events_path,
        "examiner",
        "evaluate",
        str(task["task_id"]),
        {"task": task},
        {"gate_record": gate_record.model_dump(mode="json")},
        "domain examiner evaluated the compiled candidate with the domain gate battery.",
        cycle,
    )

    risks: list[Any] = []
    if skeptic is not None and _is_fruit_candidate(gate_record, gate_spec):
        verdict = skeptic.critique(
            {
                "factor_id": gate_record.factor_id,
                "gates": gate_record.gates,
                "formula": task["formula"],
                "mechanism": task["mechanism"],
            },
            "fruit_candidate",
            gardener_model=config.gardener_model,
        )
        risks = list(verdict.weaknesses) + list(verdict.alt_explanations)
        _emit(
            events_path,
            "skeptic",
            "skeptic_challenge",
            gate_record.factor_id,
            {"factor_id": gate_record.factor_id, "kind": "fruit_candidate"},
            {"verdict": verdict.verdict, "severity": verdict.severity, "risks": risks},
            "skeptic challenged a fruit-candidate pre-G7; recorded only, never vetoes gates.",
            cycle,
        )

    align = domain.align_request(
        gate_record.factor_id,
        str(task["mechanism"]),
        {"gates": gate_record.gates, "formula": task["formula"]},
    )
    g7_response = handoff.request(
        "g7_alignment",
        {"rubric": align.rubric, "request": _public_dict(align)},
        align.schema,
        req_id=f"{task['task_id']}-g7",
        timeout_s=DEFAULT_HANDOFF_TIMEOUT_S,
    )
    _merge_alignment(gate_record, g7_response)
    _emit(
        events_path,
        "aligner",
        "handoff_g7_alignment",
        gate_record.factor_id,
        {"factor_id": gate_record.factor_id, "mechanism": task["mechanism"]},
        g7_response,
        "Claude G7 alignment handoff scored mechanism-evidence alignment.",
        cycle,
    )

    classification, reason = classify_record(gate_record, gate_spec)
    _emit(
        events_path,
        "coordinator",
        "classify",
        gate_record.factor_id,
        {"gate_record": gate_record.model_dump(mode="json")},
        {"classification": classification, "reason": reason},
        "complete gate evidence was classified into rainforest result taxonomy.",
        cycle,
    )
    return ResultRecord(
        result_id=f"result_{task['task_id']}",
        task_id=str(task["task_id"]),
        execution_mode=gate_record.execution_mode,
        classification=classification,
        summary=f"{task['formula']} classified as {classification}",
        classification_reason=reason,
        risks=risks,
        blocked_from_reuse=classification == "sick_leaf",
        gate_record=gate_record,
    )


def _is_fruit_candidate(gate_record: GateRecord, gate_spec: list[GateDef]) -> bool:
    hard_gates = [gate_def for gate_def in gate_spec if gate_def.hard]
    if not hard_gates:
        return False
    return all(_gate_passed(gate_record.gates.get(gate_def.name, {})) for gate_def in hard_gates)


def _gate_passed(gate: dict[str, Any]) -> bool:
    value = gate.get("passed")
    if isinstance(value, bool):
        return value
    score = gate.get("score")
    if isinstance(score, int | float):
        return score > 0
    return False


def _merge_alignment(gate_record: GateRecord, response: dict[str, Any]) -> None:
    score = response.get("score")
    passed = isinstance(score, int | float) and float(score) >= 1.0
    payload = {**response, "passed": passed}
    if "alignment" in gate_record.gates:
        gate_record.gates["alignment"].update(payload)
    gate_record.gates["G7"] = payload


def _styled_logic(base_logic: str, temperature: float) -> str:
    if temperature <= 0.85:
        hint = "favor robust, well-established mechanisms"
    elif temperature >= 1.15:
        hint = "favor novel, exploratory mechanisms"
    else:
        hint = "balance robustness and novelty"
    return f"{base_logic} [gardener style: {hint}]"


def _revision_logic(core_logic: str, verdict: Any) -> str:
    weaknesses = "; ".join(getattr(verdict, "weaknesses", []) or [])
    return f"{core_logic} [revise to address: {weaknesses}]"


def _taboos(forest: Any) -> list[str]:
    taboos = [warning.get("reason", "") for warning in forest.sick_leaf_warnings]
    return [str(item) for item in taboos if str(item).strip()]


def _explored(forest: Any) -> list[str]:
    return [branch.hypothesis for tree in forest.trees for branch in tree.branches]


def _scores_from_judgment(judgment: Judgment) -> dict[str, float]:
    cost = {"low": 0.2, "medium": 0.5, "high": 0.9}.get(judgment.validation_cost.lower(), 0.5)
    return {
        "novelty": float(judgment.novelty_score),
        "logic_strength": 1.0 if judgment.logic_consistent else 0.0,
        "option_value": min(max(float(judgment.alignment_score) / 3.0, 0.0), 1.0),
        "cross_tree_potential": 0.3,
        "regime_relevance": 0.5,
        "evidence_hint": 0.5,
        "data_availability": 1.0,
        "validation_cost": cost,
        "leakage_risk": 1.0 if judgment.lookahead_detected else 0.0,
        "redundancy": 0.1,
    }


def _formula_from_text(text: str) -> str:
    """Extract a single DSL expression from pseudocode (may be multi-line with assignments)."""
    stripped = text.strip()
    if not stripped:
        raise ValueError("candidate formula must be non-empty")
    lines = [ln.strip() for ln in re.split(r'[;\n]', stripped) if ln.strip()]
    if len(lines) == 1:
        m = re.match(r'^[A-Za-z_]\w*\s*=\s*(.+)$', lines[0])
        return m.group(1).strip() if m else lines[0]
    # Multi-statement (newline or semicolon-separated): inline assignments, return last expression
    env: dict[str, str] = {}
    last_expr = stripped
    for line in lines:
        m = re.match(r'^([A-Za-z_]\w*)\s*=\s*(.+)$', line)
        if m:
            varname, rhs = m.group(1), m.group(2).strip()
            env[varname] = _substitute_vars(rhs, env)
            last_expr = env[varname]
        else:
            last_expr = _substitute_vars(line, env)
    return last_expr


def _substitute_vars(expr: str, env: dict[str, str]) -> str:
    for name in sorted(env, key=len, reverse=True):
        expr = re.sub(rf'\b{re.escape(name)}\b', env[name], expr)
    return expr


def _unique_id(prefix: str, used_ids: set[str]) -> str:
    candidate = prefix
    idx = 1
    while candidate in used_ids:
        idx += 1
        candidate = f"{prefix}_{idx}"
    used_ids.add(candidate)
    return candidate


def _public_dict(item: Any) -> dict[str, Any]:
    if hasattr(item, "model_dump"):
        data = item.model_dump(mode="json")
        return data if isinstance(data, dict) else {"value": data}
    if is_dataclass(item) and not isinstance(item, type):
        data = asdict(cast(Any, item))
        return data if isinstance(data, dict) else {"value": data}
    if hasattr(item, "__dict__"):
        return dict(item.__dict__)
    return {"value": item}


def _emit(
    events_path: Path,
    role_name: str,
    action: str,
    target: str,
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    reason: str,
    cycle: int,
) -> None:
    events.emit(
        "Codex",
        role_name,
        action,
        target,
        inputs=inputs,
        outputs=outputs,
        reason=f"{role(role_name)}: {reason}",
        cycle=cycle,
        events_path=events_path,
    )


__all__ = [
    "DeliberationConfig",
    "ParallelGardenersConfig",
    "TreeDeliberation",
    "deliberate_tree",
]
