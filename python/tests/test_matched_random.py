from __future__ import annotations

from rainforest_lab.dsl.types import OpDef, OpRegistry
from rainforest_lab.gates.matched_random import matched_random_threshold


def _registry() -> OpRegistry:
    reg = OpRegistry()
    for f in ("close", "volume"):
        reg.register_field(f)
    reg.register(OpDef("cs_rank", 1, "unary", lambda s: s))
    return reg


def test_matched_random_returns_threshold_with_provenance() -> None:
    sharpes = [-0.5, 0.0, 0.3, 0.7, 1.5, 2.1, 0.4, 0.6, 0.9, 1.0]

    def evaluate(formula: str) -> float:
        return sharpes[len(formula) % len(sharpes)]

    result = matched_random_threshold(
        registry=_registry(),
        evaluate=evaluate,
        n=100,
        percentile=95,
        seed=0,
        provenance={"universe": "demo", "date": "2024-01-01"},
    )
    assert "value" in result and isinstance(result["value"], float)
    assert "provenance" in result
    assert result["provenance"]["N"] == 100 and result["provenance"]["percentile"] == 95


def test_matched_random_is_deterministic_for_same_seed() -> None:
    def evaluate(formula: str) -> float:
        return float(len(formula))

    a = matched_random_threshold(_registry(), evaluate, n=50, percentile=95, seed=42,
                                 provenance={"x": 1})
    b = matched_random_threshold(_registry(), evaluate, n=50, percentile=95, seed=42,
                                 provenance={"x": 1})
    assert a["value"] == b["value"]
