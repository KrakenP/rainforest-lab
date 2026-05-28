from __future__ import annotations

import pytest

from rainforest_lab.domain import FeatureSpace
from rainforest_lab.llm.builders import (
    make_llm_aligner,
    make_llm_gardener,
    make_llm_inspector,
    make_llm_skeptic,
)
from rainforest_lab.llm.protocols import (
    AlignRequest,
    Gardener,
    Inspector,
    Mechanism,
    Skeptic,
    SkepticVerdict,
)


def _fake_completion(payload: str):
    def call(system: str, user: str) -> str:
        return payload
    return call


_GARDENER_JSON = (
    '{"mechanisms": [{"name":"a","intuition":"i","pseudocode":"momentum:5",'
    '"regime_suggestion":"normal","lookahead_risk":"none"}]}'
)
_INSPECTOR_JSON = (
    '{"logic_consistent": true, "lookahead_detected": false, "novelty_score": 0.8,'
    ' "alignment_score": 2, "validation_cost": "low", "concerns": "none"}'
)
_SKEPTIC_JSON = (
    '{"weaknesses": ["short sample"], "overfit_risk": "high",'
    ' "alt_explanations": ["beta exposure"], "lookahead_suspicion": false,'
    ' "verdict": "revise", "severity": "medium"}'
)
_ALIGNER_JSON = '{"score": 2, "reason": "aligned"}'


def test_make_llm_gardener_parses() -> None:
    g: Gardener = make_llm_gardener(_fake_completion(_GARDENER_JSON))
    ms = g.mine("goal", FeatureSpace(["close"], ["momentum"]), [], [], 1)
    assert len(ms) == 1 and ms[0].name == "a"


def test_make_llm_gardener_n_mismatch_raises() -> None:
    g: Gardener = make_llm_gardener(_fake_completion(_GARDENER_JSON))
    with pytest.raises(ValueError, match="expected 2"):
        g.mine("goal", FeatureSpace(["close"], ["momentum"]), [], [], 2)


def test_make_llm_inspector_parses() -> None:
    i: Inspector = make_llm_inspector(_fake_completion(_INSPECTOR_JSON))
    j = i.judge(Mechanism("m", "i", "f", "r", "none"))
    assert j.alignment_score == 2 and j.logic_consistent is True


def test_make_llm_skeptic_enforces_family() -> None:
    s = make_llm_skeptic(_fake_completion(_SKEPTIC_JSON), model_family="anthropic")
    with pytest.raises(ValueError, match="anti-self-favoring"):
        s.critique({"name": "m"}, "hypothesis", gardener_model="anthropic-claude-opus")


def test_make_llm_skeptic_accepts_different_family() -> None:
    s: Skeptic = make_llm_skeptic(_fake_completion(_SKEPTIC_JSON), model_family="anthropic")
    v: SkepticVerdict = s.critique({"name": "m"}, "hypothesis", gardener_model="openai-gpt-5")
    assert v.verdict == "revise" and v.severity == "medium"


def test_make_llm_skeptic_hard_fails_on_completion_error() -> None:
    def boom(system: str, user: str) -> str:
        raise RuntimeError("provider down")
    s = make_llm_skeptic(boom, model_family="anthropic")
    with pytest.raises(RuntimeError, match="provider down"):
        s.critique({"name": "m"}, "hypothesis", gardener_model="kimi")


def test_make_llm_skeptic_rejects_malformed_json() -> None:
    s = make_llm_skeptic(_fake_completion('{"verdict": "revise"}'), model_family="anthropic")
    with pytest.raises(ValueError):
        s.critique({"name": "m"}, "hypothesis", gardener_model="kimi")


def test_make_llm_aligner_parses() -> None:
    a = make_llm_aligner(_fake_completion(_ALIGNER_JSON))
    resp = a.align(AlignRequest("f1", "mech", {}, "0-3", {"type": "object"}))
    assert resp.score == 2
