"""Quick start: one cycle on DemoDomain with mock LLMs.

Run from this directory:
    cd python/examples && python quick_start.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rainforest_lab import (
    Climate,
    DeliberationConfig,
    DemoDomain,
    Forest,
    MockGardener,
    MockInspector,
    MockSkeptic,
    ParallelGardenersConfig,
    Tree,
    run_cycle,
)


def _starter() -> Forest:
    return Forest(
        forest_id="quick_start", cycle_id="cycle_000",
        research_goal="demo alpha", domain="demo",
        constraints=[], approval_policy="manual",
        climate=Climate(
            mode="exploration", temperature=1.0, seed_budget=0.25,
            seed_slots=2, max_tree_share=0.5,
            max_consecutive_depth=3, novelty_weight=0.35,
        ),
        data_soil={"ready": True},
        trees=[Tree(tree_id="tree_a", name="A", core_logic="momentum",
                    status="active", weather_priors={"moisture": 0.7})],
        summary="initial",
    )


class _Handoff:
    """Stub handoff that auto-answers divergence + G7.

    In production use ``rainforest_lab.handoff`` (filesystem-based) or the v0.2.0 MCP server (which
    routes the handoff through MCP sampling to the host agent's LLM)."""

    def request(self, kind: str, payload: dict[str, Any], schema: dict[str, Any],
                *, req_id: str, timeout_s: int) -> dict[str, Any]:
        if kind == "divergence":
            return {"candidates": []}
        return {"score": 2, "reason": "aligned"}


def main() -> None:
    archive = Path("./runs/quick_start")
    domain = DemoDomain(seed=7)
    forest = _starter()
    cycle1 = run_cycle(
        forest, domain, archive_root=archive,
        kimi=MockGardener(), deepseek=MockInspector(), handoff=_Handoff(),
        skeptic=MockSkeptic(),
        deliberation=DeliberationConfig(max_debate_rounds=1),
        parallel=ParallelGardenersConfig(max_concurrent=1, temperature_spread=(1.0,)),
    )
    fruits = sum(1 for r in cycle1.results if r.classification == "fruit")
    golden = sum(1 for r in cycle1.results if r.classification == "golden_leaf")
    print(
        f"cycle 1: {len(cycle1.results)} results, "
        f"{fruits} fruit, {golden} golden_leaf — archived under {archive}"
    )


if __name__ == "__main__":
    main()
