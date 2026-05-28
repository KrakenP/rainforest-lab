from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from rainforest_lab.domains.demo import DemoDomain
from rainforest_lab.llm.protocols import Judgment, Mechanism
from rainforest_lab.state import Climate, Forest, Tree, load_forest
from rainforest_lab.validate import ForestValidationError, validate_forest


def _grounded_demo_forest() -> Forest:
    return Forest(
        forest_id="rl_demo_smoke",
        cycle_id="cycle_000",
        research_goal="Find robust demo alpha",
        domain="demo",
        constraints=["no leakage", "bounded validation"],
        approval_policy="manual",
        climate=Climate(
            mode="exploration",
            temperature=1.0,
            seed_budget=0.25,
            seed_slots=2,
            max_tree_share=0.50,
            max_consecutive_depth=3,
            novelty_weight=0.35,
        ),
        data_soil={"ready": True},
        trees=[
            Tree(
                tree_id="demo_tree",
                name="Demo Momentum",
                core_logic="recent price movement can persist or reverse",
                status="active",
                weather_priors={"moisture": 0.7, "clear_next_validation": True},
            )
        ],
        summary="demo smoke grounding",
    )


class MockKimi:
    def mine(
        self,
        domain_logic: str,
        feature_space: Any,
        taboos: list[str],
        explored: list[str],
        n: int,
    ) -> list[Mechanism]:
        return [
            Mechanism(
                name="demo_momentum",
                intuition="recent winners continue briefly",
                pseudocode="momentum:5",
                regime_suggestion="normal",
                lookahead_risk="none",
            ),
            Mechanism(
                name="demo_reversal",
                intuition="short-term overreaction reverts",
                pseudocode="reversal:3",
                regime_suggestion="choppy",
                lookahead_risk="none",
            ),
        ]


class MockDeepSeek:
    def judge(self, mechanism: Mechanism) -> Judgment:
        return Judgment(
            logic_consistent=True,
            lookahead_detected=False,
            novelty_score=0.8,
            alignment_score=2,
            validation_cost="low",
            concerns="none",
        )


@dataclass
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
            return {
                "candidates": [
                    {
                        "name": "handoff_momentum",
                        "formula": "momentum:5",
                        "reason": "divergent but bounded demo candidate",
                    }
                ]
            }
        return {"score": 2, "reason": "mechanism and evidence are aligned"}


def test_demo_cycle_end_to_end(tmp_path: Path) -> None:
    from rainforest_lab.cycle import run_cycle

    domain = DemoDomain(seed=7)
    forest = _grounded_demo_forest()
    validate_forest(forest, domain.gate_spec())

    cycle_1 = run_cycle(
        forest,
        domain,
        archive_root=tmp_path,
        kimi=MockKimi(),
        deepseek=MockDeepSeek(),
        handoff=MockHandoff(),
    )
    cycle_2 = run_cycle(
        cycle_1,
        domain,
        archive_root=tmp_path,
        kimi=MockKimi(),
        deepseek=MockDeepSeek(),
        handoff=MockHandoff(),
    )

    validate_forest(cycle_1, domain.gate_spec())
    validate_forest(cycle_2, domain.gate_spec())
    assert (tmp_path / "cycle_001" / "forest-state.yaml").exists()
    assert (tmp_path / "cycle_002" / "forest-state.yaml").exists()
    archived = load_forest(tmp_path / "cycle_002")
    assert any(result.classification is not None for result in archived.results)
    assert archived.results
    assert all(result.execution_mode for result in archived.results)
    assert (tmp_path / "events.jsonl").exists()
    lines = (tmp_path / "events.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 6
    assert any('"role": "examiner"' in line for line in lines)


def test_cycle_refuses_on_validation_violation(tmp_path: Path) -> None:
    from rainforest_lab.cycle import run_cycle

    domain = DemoDomain(seed=7)
    forest = _grounded_demo_forest()
    forest.trees[0].recent_budget_share = 0.99

    with pytest.raises(ForestValidationError):
        run_cycle(
            forest,
            domain,
            archive_root=tmp_path,
            kimi=MockKimi(),
            deepseek=MockDeepSeek(),
            handoff=MockHandoff(),
        )

    assert not list(tmp_path.glob("cycle_*"))
