"""LLM builders — turn any synchronous completion function into a Protocol implementation.

A completion function has signature ``(system: str, user: str) -> str`` and must return the LLM's
text. The builder owns the system prompt, the user-payload JSON, the response JSON parse, and the
adversarial framing for skeptic. No silent fallback: every parse/call failure raises."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, Literal

from rainforest_lab.domain import FeatureSpace
from rainforest_lab.llm.protocols import (
    Aligner,
    AlignRequest,
    AlignResponse,
    Gardener,
    Inspector,
    Judgment,
    Mechanism,
    Skeptic,
    SkepticVerdict,
)

CompletionFn = Callable[[str, str], str]


def make_llm_gardener(completion_fn: CompletionFn) -> Gardener:
    """Wrap a completion function as a Gardener that mines N mechanisms."""

    class _LLMGardener:
        def mine(
            self,
            domain_logic: str,
            feature_space: FeatureSpace,
            taboos: list[str],
            explored: list[str],
            n: int,
        ) -> list[Mechanism]:
            system = (
                "You are a research gardener. Mine original, testable factor mechanisms. "
                "Return strict JSON only and never include future information in pseudocode."
            )
            user = json.dumps(
                {
                    "domain_logic": domain_logic,
                    "feature_space": {
                        "columns": feature_space.columns,
                        "operators": feature_space.operators,
                    },
                    "taboos": taboos,
                    "explored": explored,
                    "n": n,
                    "response_schema": {
                        "mechanisms": [
                            {
                                "name": "string",
                                "intuition": "string",
                                "pseudocode": "string",
                                "regime_suggestion": "string",
                                "lookahead_risk": "string",
                            }
                        ]
                    },
                },
                sort_keys=True,
            )
            raw = completion_fn(system, user)
            return _parse_mechanisms(raw, n=n)

    return _LLMGardener()


def _parse_mechanisms(raw: str, *, n: int) -> list[Mechanism]:
    data = _loads_json(raw)
    items = data.get("mechanisms")
    if not isinstance(items, list):
        raise ValueError("response must contain a 'mechanisms' list")
    out = [
        Mechanism(
            name=_required_str(item, "name"),
            intuition=_required_str(item, "intuition"),
            pseudocode=_required_str(item, "pseudocode"),
            regime_suggestion=_required_str(item, "regime_suggestion"),
            lookahead_risk=_required_str(item, "lookahead_risk"),
        )
        for item in items
        if isinstance(item, dict)
    ]
    if len(out) != n:
        raise ValueError(f"gardener returned {len(out)} mechanisms; expected {n}")
    return out


def make_llm_inspector(completion_fn: CompletionFn) -> Inspector:
    class _LLMInspector:
        def judge(self, mechanism: Mechanism) -> Judgment:
            system = (
                "You are a research inspector. Judge one proposed factor mechanism. Return strict "
                "JSON only with keys: logic_consistent, lookahead_detected, novelty_score, "
                "alignment_score, validation_cost, concerns."
            )
            user = json.dumps(
                {
                    "mechanism": {
                        "name": mechanism.name,
                        "intuition": mechanism.intuition,
                        "pseudocode": mechanism.pseudocode,
                        "regime_suggestion": mechanism.regime_suggestion,
                        "lookahead_risk": mechanism.lookahead_risk,
                    }
                },
                sort_keys=True,
            )
            raw = completion_fn(system, user)
            return _parse_judgment(raw)

    return _LLMInspector()


def _parse_judgment(raw: str) -> Judgment:
    data = _loads_json(raw)
    return Judgment(
        logic_consistent=_required_bool(data, "logic_consistent"),
        lookahead_detected=_required_bool(data, "lookahead_detected"),
        novelty_score=_required_float(data, "novelty_score"),
        alignment_score=_required_int(data, "alignment_score"),
        validation_cost=_required_str(data, "validation_cost"),
        concerns=_required_str(data, "concerns"),
    )


def make_llm_skeptic(completion_fn: CompletionFn, *, model_family: str) -> Skeptic:
    """Wrap a completion as a Skeptic that adversarially critiques candidates.

    ``model_family`` is this skeptic's model family ("openai", "anthropic", "deepseek", "kimi",
    "google", ...). At call time the skeptic refuses to run if ``gardener_model`` is from the same
    family — that is the anti-self-favoring lever."""

    class _LLMSkeptic:
        def critique(
            self,
            item: dict[str, Any],
            kind: Literal["hypothesis", "fruit_candidate"],
            *,
            gardener_model: str,
        ) -> SkepticVerdict:
            if _same_family(gardener_model, model_family):
                raise ValueError(
                    f"skeptic model family {model_family!r} must differ from gardener "
                    f"{gardener_model!r} (anti-self-favoring)"
                )
            system = (
                "You are a research skeptic — an adversarial red-team critic. Assume the proposed "
                "factor is overfit, spurious, or contaminated by look-ahead until proven "
                "otherwise. Attack it: enumerate concrete weaknesses, propose plausible "
                "non-causal alternative explanations (e.g. beta, sector, size, or liquidity "
                "exposure), state whether you suspect look-ahead, and rate overfit risk. Return "
                "strict JSON ONLY with keys: weaknesses (array of strings), overfit_risk "
                "(low|medium|high), alt_explanations (array of strings), lookahead_suspicion "
                "(boolean), verdict (revise|proceed|reject), severity (low|medium|high)."
            )
            user = json.dumps({"kind": kind, "item": item}, sort_keys=True)
            raw = completion_fn(system, user)
            return _parse_verdict(raw)

    return _LLMSkeptic()


_RISK_VALUES = frozenset({"low", "medium", "high"})
_VERDICT_VALUES = frozenset({"revise", "proceed", "reject"})


def _parse_verdict(raw: str) -> SkepticVerdict:
    data = _loads_json(raw)
    return SkepticVerdict(
        weaknesses=_required_str_list(data, "weaknesses"),
        overfit_risk=_required_enum(data, "overfit_risk", _RISK_VALUES),  # type: ignore[arg-type]
        alt_explanations=_required_str_list(data, "alt_explanations"),
        lookahead_suspicion=_required_bool(data, "lookahead_suspicion"),
        verdict=_required_enum(data, "verdict", _VERDICT_VALUES),  # type: ignore[arg-type]
        severity=_required_enum(data, "severity", _RISK_VALUES),  # type: ignore[arg-type]
    )


def _same_family(a: str, b: str) -> bool:
    return a.split("-")[0].strip().lower() == b.split("-")[0].strip().lower()


def make_llm_aligner(completion_fn: CompletionFn) -> Aligner:
    class _LLMAligner:
        def align(self, request: AlignRequest) -> AlignResponse:
            system = (
                "You are a research aligner. Score whether the evidence supports the stated "
                "mechanism on the given rubric. Return strict JSON only with keys: score (integer "
                "0-3), reason (string)."
            )
            user = json.dumps(
                {
                    "factor_id": request.factor_id,
                    "mechanism": request.mechanism,
                    "evidence": request.evidence,
                    "rubric": request.rubric,
                    "response_schema": request.schema,
                },
                sort_keys=True,
                default=str,
            )
            raw = completion_fn(system, user)
            data = _loads_json(raw)
            return AlignResponse(
                score=_required_int(data, "score"),
                reason=_required_str(data, "reason"),
            )

    return _LLMAligner()


def _loads_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("response must be a JSON object")
    return data


def _required_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"field {key!r} must be a non-empty string")
    return value


def _required_bool(data: dict[str, Any], key: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"field {key!r} must be a bool")
    return value


def _required_float(data: dict[str, Any], key: str) -> float:
    value = data.get(key)
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ValueError(f"field {key!r} must be numeric")
    return float(value)


def _required_int(data: dict[str, Any], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"field {key!r} must be an int")
    return value


def _required_str_list(data: dict[str, Any], key: str) -> list[str]:
    value = data.get(key)
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"field {key!r} must be a list of strings")
    return list(value)


def _required_enum(data: dict[str, Any], key: str, allowed: frozenset[str]) -> str:
    value = data.get(key)
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"field {key!r} must be one of {sorted(allowed)}")
    return value


__all__ = [
    "CompletionFn",
    "make_llm_aligner",
    "make_llm_gardener",
    "make_llm_inspector",
    "make_llm_skeptic",
]
