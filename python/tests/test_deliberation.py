from __future__ import annotations

from pathlib import Path
from typing import Any

from rainforest_lab.deliberation import DeliberationConfig, TreeDeliberation, deliberate_tree
from rainforest_lab.domains.demo import DemoDomain
from rainforest_lab.llm.protocols import Judgment, Mechanism, SkepticVerdict
from rainforest_lab.state import Climate, Forest, Tree

_SLOTS = 2


def _forest(slots: int = _SLOTS) -> Forest:
    return Forest(
        forest_id="rl_delib",
        cycle_id="cycle_000",
        research_goal="find demo alpha",
        domain="demo",
        constraints=[],
        approval_policy="manual",
        climate=Climate(
            mode="exploration",
            temperature=1.0,
            seed_budget=0.25,
            seed_slots=slots,
            max_tree_share=0.5,
            max_consecutive_depth=3,
            novelty_weight=0.35,
        ),
        data_soil={"ready": True},
        trees=[
            Tree(
                tree_id="demo_tree",
                name="Demo",
                core_logic="momentum persists",
                status="active",
                weather_priors={"moisture": 0.7},
            )
        ],
        summary="t",
    )


class _Kimi:
    def __init__(self) -> None:
        self.calls = 0

    def mine(
        self, logic: str, fs: Any, taboos: list[str], explored: list[str], n: int
    ) -> list[Mechanism]:
        self.calls += 1
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


class _DeepSeek:
    def judge(self, m: Mechanism) -> Judgment:
        return Judgment(True, False, 0.8, 2, "low", "none")


class _Skeptic:
    def __init__(self, verdict: str = "proceed", severity: str = "low") -> None:
        self.verdict = verdict
        self.severity = severity
        self.calls: list[tuple[str, str]] = []

    def critique(
        self,
        item: dict[str, Any],
        kind: str,
        *,
        gardener_model: str,
    ) -> SkepticVerdict:
        self.calls.append((kind, gardener_model))
        return SkepticVerdict(
            weaknesses=["w"],
            overfit_risk="medium",
            alt_explanations=["beta"],
            lookahead_suspicion=False,
            verdict=self.verdict,  # type: ignore[arg-type]
            severity=self.severity,  # type: ignore[arg-type]
        )


class _Handoff:
    def request(
        self,
        kind: str,
        payload: dict[str, Any],
        schema: dict[str, Any],
        *,
        req_id: str,
        timeout_s: int,
    ) -> dict[str, Any]:
        if kind == "divergence":
            return {"candidates": []}
        return {"score": 2, "reason": "aligned"}


def _run(
    tmp_path: Path, *, rounds: int, skeptic: Any, kimi: Any = None
) -> tuple[TreeDeliberation, Any]:
    domain = DemoDomain(seed=7)
    forest = _forest()
    kimi = kimi or _Kimi()
    td = deliberate_tree(
        forest.trees[0],
        forest,
        domain,
        temperature=1.0,
        config=DeliberationConfig(max_debate_rounds=rounds),
        gardener=kimi,
        skeptic=skeptic,
        deepseek=_DeepSeek(),
        handoff=_Handoff(),
        events_path=tmp_path / "events.jsonl",
        cycle=0,
        promoted_pool={},
    )
    return td, kimi


def test_zero_rounds_skips_debate(tmp_path: Path) -> None:
    sk = _Skeptic()
    td, _ = _run(tmp_path, rounds=0, skeptic=sk)
    assert all(kind != "hypothesis" for (kind, *_rest) in sk.calls)
    assert td.records  # produced at least one evaluated candidate


def test_debate_is_bounded(tmp_path: Path) -> None:
    sk = _Skeptic(verdict="revise", severity="low")
    kimi = _Kimi()
    _td, _ = _run(tmp_path, rounds=2, skeptic=sk, kimi=kimi)
    hyp_calls = [c for c in sk.calls if c[0] == "hypothesis"]
    # initial mine (1) + at most rounds re-mines per surviving mechanism; finite & bounded
    assert kimi.calls <= 1 + 2 * _SLOTS
    assert hyp_calls  # debate actually happened


def test_reject_high_culls_mechanism(tmp_path: Path) -> None:
    sk = _Skeptic(verdict="reject", severity="high")
    td, _ = _run(tmp_path, rounds=1, skeptic=sk)
    assert td.records == []  # all mechanisms culled, divergence empty -> no candidates


def test_skeptic_uses_different_model(tmp_path: Path) -> None:
    sk = _Skeptic(verdict="proceed")
    _run(tmp_path, rounds=1, skeptic=sk)
    assert sk.calls
    for (_kind, gardener_model) in sk.calls:
        assert gardener_model == "kimi"


def test_deliberation_is_pure(tmp_path: Path) -> None:
    sk = _Skeptic(verdict="proceed")
    domain = DemoDomain(seed=7)
    forest = _forest()
    snapshot = forest.model_dump(mode="json")
    deliberate_tree(
        forest.trees[0],
        forest,
        domain,
        temperature=1.0,
        config=DeliberationConfig(max_debate_rounds=1),
        gardener=_Kimi(),
        skeptic=sk,
        deepseek=_DeepSeek(),
        handoff=_Handoff(),
        events_path=tmp_path / "e.jsonl",
        cycle=0,
        promoted_pool={},
    )
    assert forest.model_dump(mode="json") == snapshot  # forest untouched
