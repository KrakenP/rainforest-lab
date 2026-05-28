from __future__ import annotations

from pathlib import Path
from typing import Any

from rainforest_lab import (
    DeliberationConfig,
    DemoDomain,
    Forest,
    MockGardener,
    MockInspector,
    MockSkeptic,
    ParallelGardenersConfig,
    __version__,
    run_cycle,
    validate_forest,
)
from rainforest_lab.state import Climate, Tree


def _starter_forest() -> Forest:
    return Forest(
        forest_id="facade_test",
        cycle_id="cycle_000",
        research_goal="demo",
        domain="demo",
        constraints=[],
        approval_policy="manual",
        climate=Climate(
            mode="exploration", temperature=1.0, seed_budget=0.25,
            seed_slots=2, max_tree_share=0.5, max_consecutive_depth=3,
            novelty_weight=0.35,
        ),
        data_soil={"ready": True},
        trees=[
            Tree(tree_id="tree_a", name="A", core_logic="momentum",
                 status="active", weather_priors={"moisture": 0.7}),
        ],
        summary="t",
    )


class _Handoff:
    def request(self, kind: str, payload: dict[str, Any], schema: dict[str, Any],
                *, req_id: str, timeout_s: int) -> dict[str, Any]:
        if kind == "divergence":
            return {"candidates": []}
        return {"score": 2, "reason": "aligned"}


def test_version_string() -> None:
    assert __version__ == "0.1.0"


def test_v1_smoke_one_cycle(tmp_path: Path) -> None:
    domain = DemoDomain(seed=7)
    forest = _starter_forest()
    validate_forest(forest, domain.gate_spec())

    next_forest = run_cycle(
        forest, domain, archive_root=tmp_path,
        kimi=MockGardener(), deepseek=MockInspector(), handoff=_Handoff(),
    )
    validate_forest(next_forest, domain.gate_spec())
    assert (tmp_path / "cycle_001" / "forest-state.yaml").exists()


def test_v2_smoke_with_skeptic(tmp_path: Path) -> None:
    domain = DemoDomain(seed=7)
    forest = _starter_forest()

    next_forest = run_cycle(
        forest, domain, archive_root=tmp_path,
        kimi=MockGardener(), deepseek=MockInspector(), handoff=_Handoff(),
        skeptic=MockSkeptic(),
        deliberation=DeliberationConfig(max_debate_rounds=1),
        parallel=ParallelGardenersConfig(max_concurrent=1, temperature_spread=(1.0,)),
    )
    validate_forest(next_forest, domain.gate_spec())
    assert (tmp_path / "cycle_001" / "forest-state.yaml").exists()
