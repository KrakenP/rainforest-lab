from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from rainforest_lab.cycle import run_cycle
from rainforest_lab.deliberation import DeliberationConfig, ParallelGardenersConfig
from rainforest_lab.domains.demo import DemoDomain
from rainforest_lab.llm.protocols import Judgment, Mechanism, SkepticVerdict
from rainforest_lab.state import Climate, Forest, Tree
from rainforest_lab.validate import validate_forest


class MockKimi:
    def mine(
        self, logic: str, fs: Any, taboos: list[str], explored: list[str], n: int
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


class MockDeepSeek:
    def judge(self, m: Mechanism) -> Judgment:
        return Judgment(True, False, 0.8, 2, "low", "none")


class MockSkeptic:
    def __init__(self, verdict: str = "proceed", severity: str = "low") -> None:
        self.verdict = verdict
        self.severity = severity

    def critique(
        self,
        item: dict[str, Any],
        kind: str,
        *,
        gardener_model: str,
    ) -> SkepticVerdict:
        return SkepticVerdict(
            weaknesses=["w"],
            overfit_risk="medium",
            alt_explanations=["beta"],
            lookahead_suspicion=False,
            verdict=self.verdict,  # type: ignore[arg-type]
            severity=self.severity,  # type: ignore[arg-type]
        )


class MockHandoff:
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


def _two_tree_forest() -> Forest:
    return Forest(
        forest_id="rl_v2",
        cycle_id="cycle_000",
        research_goal="find demo alpha",
        domain="demo",
        constraints=[],
        approval_policy="manual",
        climate=Climate(
            mode="exploration",
            temperature=1.0,
            seed_budget=0.25,
            seed_slots=2,
            max_tree_share=0.5,
            max_consecutive_depth=3,
            novelty_weight=0.35,
        ),
        data_soil={"ready": True},
        trees=[
            Tree(
                tree_id="tree_a",
                name="A",
                core_logic="momentum persists",
                status="active",
                weather_priors={"moisture": 0.7},
            ),
            Tree(
                tree_id="tree_b",
                name="B",
                core_logic="reversal after spikes",
                status="active",
                weather_priors={"moisture": 0.7},
            ),
        ],
        summary="t",
    )


def _classifications(forest: Forest) -> dict[str, str | None]:
    return {
        r.gate_record.factor_id: r.classification
        for r in forest.results
        if r.gate_record is not None
    }


def _v2_kwargs(rounds: int = 2, **over: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = dict(
        kimi=MockKimi(),
        deepseek=MockDeepSeek(),
        handoff=MockHandoff(),
        skeptic=MockSkeptic(),
        deliberation=DeliberationConfig(max_debate_rounds=rounds),
        parallel=ParallelGardenersConfig(max_concurrent=4, temperature_spread=(0.7, 1.0, 1.3)),
    )
    kwargs.update(over)
    return kwargs


def test_v2_requires_skeptic(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        run_cycle(
            _two_tree_forest(),
            DemoDomain(seed=7),
            archive_root=tmp_path,
            kimi=MockKimi(),
            deepseek=MockDeepSeek(),
            handoff=MockHandoff(),
            skeptic=None,
            deliberation=DeliberationConfig(max_debate_rounds=1),
        )


def test_v2_merge_is_reproducible(tmp_path: Path) -> None:
    a = run_cycle(
        _two_tree_forest(), DemoDomain(seed=7), archive_root=tmp_path / "a", **_v2_kwargs()
    )
    b = run_cycle(
        _two_tree_forest(), DemoDomain(seed=7), archive_root=tmp_path / "b", **_v2_kwargs()
    )
    validate_forest(a, DemoDomain(seed=7).gate_spec())
    assert _classifications(a) == _classifications(b)
    assert [t.task_id for t in a.results] == [t.task_id for t in b.results]


def test_v2_zero_rounds_matches_v1_classifications(tmp_path: Path) -> None:
    domain = DemoDomain(seed=7)
    v1 = run_cycle(
        _two_tree_forest(),
        domain,
        archive_root=tmp_path / "v1",
        kimi=MockKimi(),
        deepseek=MockDeepSeek(),
        handoff=MockHandoff(),
    )
    v2 = run_cycle(
        _two_tree_forest(),
        DemoDomain(seed=7),
        archive_root=tmp_path / "v2",
        kimi=MockKimi(),
        deepseek=MockDeepSeek(),
        handoff=MockHandoff(),
        skeptic=MockSkeptic(verdict="proceed"),
        deliberation=DeliberationConfig(max_debate_rounds=0),
        parallel=ParallelGardenersConfig(max_concurrent=1, temperature_spread=(1.0,)),
    )
    # skeptic 2nd-challenge never changes gate outcomes -> identical classification value set
    assert set(_classifications(v1).values()) == set(_classifications(v2).values())


def test_v2_full_smoke_validator_green(tmp_path: Path) -> None:
    forest = _two_tree_forest()
    domain = DemoDomain(seed=7)
    validate_forest(forest, domain.gate_spec())
    c1 = run_cycle(forest, domain, archive_root=tmp_path, **_v2_kwargs())
    c2 = run_cycle(c1, domain, archive_root=tmp_path, **_v2_kwargs())
    validate_forest(c1, domain.gate_spec())
    validate_forest(c2, domain.gate_spec())
    assert (tmp_path / "cycle_001" / "forest-state.yaml").exists()
    assert (tmp_path / "cycle_002" / "forest-state.yaml").exists()
    assert c2.results
    assert all(r.execution_mode for r in c2.results)
    lines = (tmp_path / "events.jsonl").read_text(encoding="utf-8").splitlines()
    assert any('"action": "gardener_parallel_dispatch"' in ln for ln in lines)
    assert any('"action": "debate_round"' in ln for ln in lines)
    assert any('"action": "skeptic_challenge"' in ln for ln in lines)


def test_skeptic_reject_cannot_veto_passing_fruit(tmp_path: Path) -> None:
    # A legit fruit (all hard gates pass, tool_executed, G7=2) stays fruit even if skeptic rejects.
    forest = _two_tree_forest()
    domain = DemoDomain(seed=7)
    out = run_cycle(
        forest,
        domain,
        archive_root=tmp_path,
        kimi=MockKimi(),
        deepseek=MockDeepSeek(),
        handoff=MockHandoff(),
        skeptic=MockSkeptic(verdict="reject", severity="high"),
        deliberation=DeliberationConfig(max_debate_rounds=0),  # no cull at hypothesis stage
        parallel=ParallelGardenersConfig(),
    )
    fruits = [r for r in out.results if r.classification == "fruit"]
    for r in fruits:
        assert r.execution_mode == "tool_executed"
    validate_forest(out, domain.gate_spec())  # rigor invariant holds


def test_debated_stub_cannot_become_fruit() -> None:
    # A stub gate_record favorably debated still cannot classify as fruit.
    from rainforest_lab.classify import classify
    from rainforest_lab.state import GateDef, GateRecord

    spec = [GateDef(name="G1", hard=True), GateDef(name="G7", hard=False, needs_handoff=True)]
    stub = GateRecord(
        domain="demo",
        factor_id="stub_x",
        gates={"G1": {"passed": True}, "G7": {"score": 2}},
        execution_mode="stub_result",
    )
    with pytest.raises(ValueError):
        classify(stub, spec)  # fruit path requires tool_executed -> raises on stub
