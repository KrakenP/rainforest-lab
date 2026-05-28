"""Test mocks for the four LLM Protocols. Deterministic, no LLM calls."""

from __future__ import annotations

from typing import Any, Literal

from rainforest_lab.domain import FeatureSpace
from rainforest_lab.llm.protocols import (
    AlignRequest,
    AlignResponse,
    Judgment,
    Mechanism,
    SkepticVerdict,
)


class MockGardener:
    def mine(
        self,
        domain_logic: str,
        feature_space: FeatureSpace,
        taboos: list[str],
        explored: list[str],
        n: int,
    ) -> list[Mechanism]:
        return [
            Mechanism(
                name=f"m{i}",
                intuition="x",
                pseudocode="momentum:5",
                regime_suggestion="normal",
                lookahead_risk="none",
            )
            for i in range(n)
        ]


class MockInspector:
    def judge(self, mechanism: Mechanism) -> Judgment:
        return Judgment(True, False, 0.8, 2, "low", "none")


class MockSkeptic:
    def __init__(
        self,
        verdict: Literal["revise", "proceed", "reject"] = "proceed",
        severity: Literal["low", "medium", "high"] = "low",
    ) -> None:
        self._verdict = verdict
        self._severity = severity

    def critique(
        self,
        item: dict[str, Any],
        kind: Literal["hypothesis", "fruit_candidate"],
        *,
        gardener_model: str,
    ) -> SkepticVerdict:
        return SkepticVerdict(
            weaknesses=["w"],
            overfit_risk="medium",
            alt_explanations=["beta"],
            lookahead_suspicion=False,
            verdict=self._verdict,
            severity=self._severity,
        )


class MockAligner:
    def align(self, request: AlignRequest) -> AlignResponse:
        return AlignResponse(score=2, reason="aligned (mock)")


__all__ = ["MockAligner", "MockGardener", "MockInspector", "MockSkeptic"]
