from __future__ import annotations

import dataclasses

import pytest

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


def test_mechanism_is_frozen() -> None:
    m = Mechanism(name="x", intuition="y", pseudocode="z",
                  regime_suggestion="r", lookahead_risk="none")
    assert dataclasses.is_dataclass(m)
    with pytest.raises(dataclasses.FrozenInstanceError):
        m.name = "renamed"  # type: ignore[misc]


def test_judgment_fields() -> None:
    j = Judgment(logic_consistent=True, lookahead_detected=False, novelty_score=0.8,
                 alignment_score=2, validation_cost="low", concerns="none")
    assert j.alignment_score == 2


def test_skeptic_verdict_enums() -> None:
    v = SkepticVerdict(
        weaknesses=["short sample"], overfit_risk="medium",
        alt_explanations=["beta"], lookahead_suspicion=False,
        verdict="proceed", severity="low",
    )
    assert v.verdict == "proceed"


def test_align_request_response_pair() -> None:
    req = AlignRequest(
        factor_id="f1", mechanism="m", evidence={},
        rubric="0-3 scale", schema={"type": "object"},
    )
    resp = AlignResponse(score=2, reason="aligned")
    assert req.rubric and resp.score == 2


def test_mocks_satisfy_protocols() -> None:
    from rainforest_lab.llm.mocks import (
        MockAligner,
        MockGardener,
        MockInspector,
        MockSkeptic,
    )
    g: Gardener = MockGardener()
    i: Inspector = MockInspector()
    s: Skeptic = MockSkeptic()
    a: Aligner = MockAligner()
    assert isinstance(g, Gardener)
    assert isinstance(i, Inspector)
    assert isinstance(s, Skeptic)
    assert isinstance(a, Aligner)


def test_mock_gardener_mines() -> None:
    from rainforest_lab.llm.mocks import MockGardener
    g = MockGardener()
    mechanisms = g.mine("logic", FeatureSpace(columns=["close"], operators=["momentum"]),
                        taboos=[], explored=[], n=3)
    assert len(mechanisms) == 3
