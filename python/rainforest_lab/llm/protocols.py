"""LLM-agnostic surfaces for the rainforest engine.

Two layers:

1. **Protocols** (this file). Any class implementing these four protocols can drive the engine.
   Use them for tight integrations (your own SDK, internal APIs, exotic providers).
2. **Builders** (``builders.py``). Higher-level: hand them a synchronous completion function
   ``(system: str, user: str) -> str`` and they return a Protocol implementation that owns the
   adversarial prompt + JSON parsing + (for skeptic) the different-model check. LiteLLM adapter
   uses these.

The dataclasses below are the payload contract between the engine and the LLM layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol, runtime_checkable

from rainforest_lab.domain import FeatureSpace


@dataclass(frozen=True)
class Mechanism:
    """A factor-mining hypothesis from the gardener."""

    name: str
    intuition: str
    pseudocode: str
    regime_suggestion: str
    lookahead_risk: str


@dataclass(frozen=True)
class Judgment:
    """An inspector's pre-nursery judgement of one mechanism."""

    logic_consistent: bool
    lookahead_detected: bool
    novelty_score: float
    alignment_score: int
    validation_cost: str
    concerns: str


@dataclass(frozen=True)
class SkepticVerdict:
    """An adversarial critic's verdict on a hypothesis or fruit-candidate."""

    weaknesses: list[str]
    overfit_risk: Literal["low", "medium", "high"]
    alt_explanations: list[str]
    lookahead_suspicion: bool
    verdict: Literal["revise", "proceed", "reject"]
    severity: Literal["low", "medium", "high"]


@dataclass(frozen=True)
class AlignRequest:
    """Aligner input — built by the domain's ``align_request()``."""

    factor_id: str
    mechanism: str
    evidence: dict[str, Any]
    rubric: str
    schema: dict[str, Any]


@dataclass(frozen=True)
class AlignResponse:
    """Aligner output — a 0-3 score with a reason."""

    score: int
    reason: str


@runtime_checkable
class Gardener(Protocol):
    """Mines N candidate mechanisms for a tree's research goal."""

    def mine(
        self,
        domain_logic: str,
        feature_space: FeatureSpace,
        taboos: list[str],
        explored: list[str],
        n: int,
    ) -> list[Mechanism]: ...


@runtime_checkable
class Inspector(Protocol):
    """Judges one mechanism on consistency, novelty, and leakage."""

    def judge(self, mechanism: Mechanism) -> Judgment: ...


@runtime_checkable
class Skeptic(Protocol):
    """Adversarial critique. MUST use a different model family than the gardener.

    Implementations raise ValueError when their model family equals ``gardener_model``."""

    def critique(
        self,
        item: dict[str, Any],
        kind: Literal["hypothesis", "fruit_candidate"],
        *,
        gardener_model: str,
    ) -> SkepticVerdict: ...


@runtime_checkable
class Aligner(Protocol):
    """G7 alignment — scores mechanism vs evidence on a 0-3 scale."""

    def align(self, request: AlignRequest) -> AlignResponse: ...


SEVERITY_ORDER: dict[str, int] = {"low": 1, "medium": 2, "high": 3}


__all__ = [
    "SEVERITY_ORDER",
    "AlignRequest",
    "AlignResponse",
    "Aligner",
    "Gardener",
    "Inspector",
    "Judgment",
    "Mechanism",
    "Skeptic",
    "SkepticVerdict",
]
