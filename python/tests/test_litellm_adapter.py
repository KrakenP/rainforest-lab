from __future__ import annotations

import sys
import types
from typing import Any

import pytest


@pytest.fixture
def fake_litellm(monkeypatch):
    """Replace litellm.completion with a stub that returns canned JSON keyed by system prompt."""

    canned = {
        "gardener": (
            '{"mechanisms":[{"name":"a","intuition":"x","pseudocode":"momentum:5",'
            '"regime_suggestion":"normal","lookahead_risk":"none"}]}'
        ),
        "inspector": (
            '{"logic_consistent":true,"lookahead_detected":false,"novelty_score":0.8,'
            '"alignment_score":2,"validation_cost":"low","concerns":"none"}'
        ),
        "skeptic": (
            '{"weaknesses":["x"],"overfit_risk":"medium","alt_explanations":["beta"],'
            '"lookahead_suspicion":false,"verdict":"proceed","severity":"low"}'
        ),
        "aligner": '{"score":2,"reason":"aligned"}',
    }

    class _Resp:
        def __init__(self, text: str) -> None:
            self.choices = [type("C", (), {"message": type("M", (), {"content": text})})]

    def fake_completion(*, model: str, messages: list[dict[str, str]], **kwargs: Any) -> _Resp:
        system = messages[0]["content"]
        if "gardener" in system:
            return _Resp(canned["gardener"])
        if "inspector" in system:
            return _Resp(canned["inspector"])
        if "skeptic" in system:
            return _Resp(canned["skeptic"])
        if "aligner" in system:
            return _Resp(canned["aligner"])
        raise AssertionError(f"unexpected system prompt: {system!r}")

    mod = types.ModuleType("litellm")
    mod.completion = fake_completion  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "litellm", mod)
    return mod


def test_litellm_gardener_returns_mechanisms(fake_litellm):
    from rainforest_lab.domain import FeatureSpace
    from rainforest_lab.llm.litellm_adapter import litellm_gardener
    g = litellm_gardener("openai/gpt-5")
    ms = g.mine("goal", FeatureSpace(["close"], ["momentum"]), [], [], 1)
    assert len(ms) == 1 and ms[0].name == "a"


def test_litellm_inspector_returns_judgment(fake_litellm):
    from rainforest_lab.llm.litellm_adapter import litellm_inspector
    from rainforest_lab.llm.protocols import Mechanism
    i = litellm_inspector("openai/gpt-5")
    j = i.judge(Mechanism("m", "i", "f", "r", "none"))
    assert j.alignment_score == 2


def test_litellm_skeptic_enforces_family(fake_litellm):
    from rainforest_lab.llm.litellm_adapter import litellm_skeptic
    s = litellm_skeptic("anthropic/claude-opus", model_family="anthropic")
    with pytest.raises(ValueError):
        s.critique({"name": "m"}, "hypothesis", gardener_model="anthropic-claude-haiku")


def test_litellm_skeptic_works_cross_family(fake_litellm):
    from rainforest_lab.llm.litellm_adapter import litellm_skeptic
    s = litellm_skeptic("anthropic/claude-opus", model_family="anthropic")
    v = s.critique({"name": "m"}, "hypothesis", gardener_model="openai-gpt-5")
    assert v.verdict == "proceed"


def test_litellm_aligner_returns_score(fake_litellm):
    from rainforest_lab.llm.litellm_adapter import litellm_aligner
    from rainforest_lab.llm.protocols import AlignRequest
    a = litellm_aligner("openai/gpt-5")
    r = a.align(AlignRequest("f1", "mech", {}, "0-3", {"type": "object"}))
    assert r.score == 2 and r.reason == "aligned"


def test_litellm_import_error_message_when_litellm_missing(monkeypatch):
    monkeypatch.setitem(sys.modules, "litellm", None)
    # force re-resolution by reimporting the function (it uses local `import litellm` inside)
    from rainforest_lab.llm.litellm_adapter import litellm_gardener
    with pytest.raises(ImportError, match=r"pip install"):
        litellm_gardener("openai/gpt-5")
