from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from rainforest_lab.llm.protocols import Mechanism
from rainforest_lab.state import GateRecord, ResultRecord, Seed
from rainforest_lab.trajectories import (
    Trajectory,
    TrajectoryStep,
    compute_reward,
    crossover,
    evolve_seeds_from_archive,
    load_trajectories,
    mutate,
    save_trajectories,
    select_parents,
    synthesize_from_result,
    trajectory_to_seed,
)

# ---------- helpers ----------


def _hypothesis_step(name: str = "m", formula: str = "momentum:5") -> TrajectoryStep:
    return TrajectoryStep(
        step_id=f"{name}_hypothesis",
        kind="hypothesis",
        actor_role="gardener",
        inputs={"seed_id": f"seed_{name}"},
        action={"name": name, "intuition": f"{name} idea", "formula": formula},
        outputs={"mechanism": {"name": name, "intuition": f"{name} idea", "pseudocode": formula}},
    )


def _examiner_step(passed_count: int = 2) -> TrajectoryStep:
    gates = {f"g{i}": {"passed": i < passed_count} for i in range(3)}
    return TrajectoryStep(
        step_id="exam",
        kind="examiner",
        actor_role="examiner",
        inputs={"factor_id": "factor_x"},
        action={"evaluation": "ran gate battery"},
        outputs={"gate_record": {"factor_id": "factor_x", "gates": gates}},
    )


def _classify_step(classification: str, risks: list[str] | None = None) -> TrajectoryStep:
    return TrajectoryStep(
        step_id="classify",
        kind="classify",
        actor_role="coordinator",
        inputs={"task_id": "task_x"},
        action={"classifier": "rainforest"},
        outputs={"classification": classification, "reason": "x", "risks": list(risks or [])},
    )


def _make_trajectory(
    classification: str | None,
    *,
    tid: str = "traj_t",
    tree_id: str = "tree_a",
    cycle_id: str = "cycle_001",
    operation: str = "genesis",
    parent_ids: list[str] | None = None,
    passed: int = 2,
    formula: str = "momentum:5",
    reward: float | None = None,
) -> Trajectory:
    steps = [_hypothesis_step(formula=formula)]
    if classification is not None:
        steps.append(_examiner_step(passed_count=passed))
        steps.append(_classify_step(classification))
    traj = Trajectory(
        trajectory_id=tid,
        cycle_id=cycle_id,
        tree_id=tree_id,
        parent_ids=parent_ids or [],
        operation=operation,  # type: ignore[arg-type]
        steps=steps,
        final_classification=classification,  # type: ignore[arg-type]
        factor_id="factor_x" if classification is not None else None,
        notes="t",
    )
    if reward is None:
        reward = compute_reward(traj)
    return traj.model_copy(update={"reward": reward})


class _MockKimi:
    """Records calls; returns a deterministic mechanism keyed by call index."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def mine(
        self, domain_logic: str, fs: Any, taboos: list[str], explored: list[str], n: int
    ) -> list[Mechanism]:
        self.calls.append(
            {"logic": domain_logic, "n": n, "taboos": list(taboos), "explored": list(explored)}
        )
        return [
            Mechanism(
                name=f"evolved_{len(self.calls)}_{i}",
                intuition=f"evolved intuition {len(self.calls)}.{i}",
                pseudocode="momentum:7",
                regime_suggestion="normal",
                lookahead_risk="none",
            )
            for i in range(n)
        ]


# ---------- reward ----------


def test_compute_reward_orders_classifications() -> None:
    fruit = _make_trajectory("fruit", passed=3, tid="t_fruit")
    golden = _make_trajectory("golden_leaf", passed=2, tid="t_golden")
    normal = _make_trajectory("normal_leaf", passed=1, tid="t_normal")
    dead = _make_trajectory("dead_leaf", passed=0, tid="t_dead")
    sick = _make_trajectory("sick_leaf", passed=0, tid="t_sick")
    assert (
        compute_reward(fruit)
        > compute_reward(golden)
        > compute_reward(normal)
        > compute_reward(dead)
        > compute_reward(sick)
    )


def test_compute_reward_penalizes_long_formula() -> None:
    short = _make_trajectory("golden_leaf", passed=2, formula="momentum:5", tid="ts")
    long = _make_trajectory("golden_leaf", passed=2, formula="x" * 500, tid="tl")
    assert compute_reward(short) > compute_reward(long)


# ---------- selection ----------


def test_select_parents_excludes_sick() -> None:
    fruit = _make_trajectory("fruit", tid="tf")
    sick = _make_trajectory("sick_leaf", tid="ts")
    golden = _make_trajectory("golden_leaf", tid="tg")
    selected = select_parents([fruit, sick, golden], k=3)
    assert sick not in selected
    assert selected[0] == fruit  # highest reward first
    assert selected[-1] == golden


def test_select_parents_deterministic_tiebreak() -> None:
    a = _make_trajectory("golden_leaf", tid="traj_a", reward=0.5)
    b = _make_trajectory("golden_leaf", tid="traj_b", reward=0.5)
    selected1 = select_parents([b, a], k=2)
    selected2 = select_parents([a, b], k=2)
    assert [t.trajectory_id for t in selected1] == ["traj_a", "traj_b"]
    assert [t.trajectory_id for t in selected1] == [t.trajectory_id for t in selected2]


# ---------- synthesize / yaml ----------


def test_synthesize_from_result_builds_trajectory() -> None:
    gate = GateRecord(
        domain="demo",
        factor_id="factor_x",
        gates={"g1": {"passed": True}, "g2": {"passed": False}},
        execution_mode="tool_executed",
    )
    result = ResultRecord(
        result_id="r1",
        task_id="task_001",
        execution_mode="tool_executed",
        classification="golden_leaf",
        summary="momentum:5 classified",
        classification_reason="weak signal",
        risks=["overfit", "beta exposure"],
        blocked_from_reuse=False,
        gate_record=gate,
    )
    seed = Seed(
        seed_id="seed_001",
        idea="momentum persists short-term",
        source_type="kimi",
        related_trees=["tree_a"],
        scores={},
        status="quarantine",
        validation_plan="momentum:5",
        reason="x",
    )
    traj = synthesize_from_result(result, seed, tree_id="tree_a", cycle_id="cycle_001")
    assert traj.operation == "genesis"
    assert traj.tree_id == "tree_a"
    assert traj.final_classification == "golden_leaf"
    assert traj.factor_id == "factor_x"
    assert traj.reward is not None
    kinds = [s.kind for s in traj.steps]
    assert "hypothesis" in kinds and "examiner" in kinds and "classify" in kinds


def test_yaml_roundtrip_preserves_all_fields(tmp_path: Path) -> None:
    a = _make_trajectory("fruit", tid="ta")
    b = _make_trajectory("golden_leaf", tid="tb")
    save_trajectories([a, b], tmp_path)
    loaded = load_trajectories(tmp_path)
    assert loaded == [a, b]


def test_load_trajectories_missing_returns_empty(tmp_path: Path) -> None:
    assert load_trajectories(tmp_path) == []


# ---------- mutation ----------


def test_mutate_lineage_and_unevaluated_child() -> None:
    parent = _make_trajectory("golden_leaf", tid="parent_a", passed=1)
    kimi = _MockKimi()
    child = mutate(
        parent,
        gardener=kimi,
        gardener_model="kimi",
        feature_space=object(),
        taboos=[],
        explored=[],
        cycle_id="cycle_002",
    )
    assert child.operation == "mutation"
    assert child.parent_ids == ["parent_a"]
    assert child.final_classification is None  # NO fruit by lineage
    assert child.factor_id is None
    assert child.reward is None
    assert child.steps[0].kind == "hypothesis"
    assert kimi.calls and kimi.calls[0]["n"] == 1


def test_mutate_refuses_sick_parent() -> None:
    sick = _make_trajectory("sick_leaf", tid="poison")
    with pytest.raises(ValueError, match="sick"):
        mutate(
            sick,
            gardener=_MockKimi(),
            gardener_model="kimi",
            feature_space=object(),
            taboos=[],
            explored=[],
            cycle_id="c",
        )


def test_mutate_id_is_content_addressable() -> None:
    parent = _make_trajectory("golden_leaf", tid="parent_same")
    kimi = _MockKimi()
    child1 = mutate(
        parent,
        gardener=kimi,
        gardener_model="kimi",
        feature_space=object(),
        taboos=[],
        explored=[],
        cycle_id="c1",
    )
    # second mutation produces a different new action (mock encodes call index in name),
    # so the trajectory_id must differ.
    child2 = mutate(
        parent,
        gardener=kimi,
        gardener_model="kimi",
        feature_space=object(),
        taboos=[],
        explored=[],
        cycle_id="c2",
    )
    assert child1.trajectory_id != child2.trajectory_id
    assert child1.trajectory_id.startswith("traj_mut_")


def test_mutate_child_cannot_be_fruit_by_lineage() -> None:
    fruit_parent = _make_trajectory("fruit", tid="fruit_p", passed=3)
    child = mutate(
        fruit_parent,
        gardener=_MockKimi(),
        gardener_model="kimi",
        feature_space=object(),
        taboos=[],
        explored=[],
        cycle_id="c",
    )
    assert child.final_classification is None
    assert compute_reward(child) <= compute_reward(fruit_parent)


# ---------- crossover ----------


def test_crossover_requires_two_healthy_parents() -> None:
    only = _make_trajectory("fruit", tid="solo")
    with pytest.raises(ValueError):
        crossover(
            [only],
            gardener=_MockKimi(),
            gardener_model="kimi",
            feature_space=object(),
            taboos=[],
            explored=[],
            cycle_id="c",
        )


def test_crossover_filters_sick() -> None:
    healthy = _make_trajectory("fruit", tid="ok")
    sick = _make_trajectory("sick_leaf", tid="bad")
    with pytest.raises(ValueError, match="healthy"):
        crossover(
            [healthy, sick],
            gardener=_MockKimi(),
            gardener_model="kimi",
            feature_space=object(),
            taboos=[],
            explored=[],
            cycle_id="c",
        )


def test_crossover_records_multi_parent_lineage() -> None:
    a = _make_trajectory("fruit", tid="pa")
    b = _make_trajectory("golden_leaf", tid="pb")
    child = crossover(
        [a, b],
        gardener=_MockKimi(),
        gardener_model="kimi",
        feature_space=object(),
        taboos=[],
        explored=[],
        cycle_id="c2",
    )
    assert child.operation == "crossover"
    assert set(child.parent_ids) == {"pa", "pb"}
    assert child.parent_ids == sorted(child.parent_ids)  # deterministic order
    assert child.final_classification is None  # NO fruit by lineage
    assert child.trajectory_id.startswith("traj_xover_")


# ---------- seed conversion ----------


def test_trajectory_to_seed_carries_hypothesis_and_lineage() -> None:
    parent = _make_trajectory("golden_leaf", tid="parent_z")
    child = mutate(
        parent,
        gardener=_MockKimi(),
        gardener_model="kimi",
        feature_space=object(),
        taboos=[],
        explored=[],
        cycle_id="cycle_002",
    )
    seed = trajectory_to_seed(child, cycle_id="cycle_002")
    assert seed.source_type == "trajectory_mutation"
    assert seed.validation_plan  # non-empty formula
    assert "parent_z" in seed.reason
    assert child.tree_id in seed.related_trees


def test_trajectory_to_seed_rejects_empty_formula() -> None:
    bad = Trajectory(
        trajectory_id="t_empty",
        cycle_id="c",
        tree_id="tree_a",
        parent_ids=[],
        operation="genesis",
        steps=[
            TrajectoryStep(
                step_id="h",
                kind="hypothesis",
                actor_role="gardener",
                inputs={},
                action={"name": "x", "intuition": "x", "formula": "   "},
                outputs={},
            )
        ],
        final_classification=None,
    )
    with pytest.raises(ValueError, match="formula"):
        trajectory_to_seed(bad, cycle_id="c2")


# ---------- e2e helper ----------


def test_evolve_seeds_from_archive_e2e(tmp_path: Path) -> None:
    pool = [
        _make_trajectory("fruit", tid="p_fruit", passed=3),
        _make_trajectory("golden_leaf", tid="p_golden", passed=2),
        _make_trajectory("normal_leaf", tid="p_normal", passed=1),
        _make_trajectory("sick_leaf", tid="p_sick"),
    ]
    save_trajectories(pool, tmp_path)
    kimi = _MockKimi()
    seeds = evolve_seeds_from_archive(
        tmp_path,
        k_mut=2,
        k_xover=1,
        gardener=kimi,
        gardener_model="kimi",
        feature_space=object(),
        taboos=[],
        explored=[],
        cycle_id="cycle_002",
        xover_parents=2,
    )
    # 2 mutation children (top 2 non-sick = fruit + golden) + 1 crossover child
    assert len(seeds) == 3
    sources = sorted(s.source_type for s in seeds)
    assert sources == ["trajectory_crossover", "trajectory_mutation", "trajectory_mutation"]
    for seed in seeds:
        assert seed.validation_plan  # all have formulas
        assert seed.status == "hold"  # not yet sown; coordinator will rank/route
    # sick was not used as parent
    for seed in seeds:
        assert "p_sick" not in seed.reason


def test_evolve_seeds_from_empty_archive_returns_empty(tmp_path: Path) -> None:
    assert evolve_seeds_from_archive(
        tmp_path,
        k_mut=2,
        k_xover=1,
        gardener=_MockKimi(),
        gardener_model="kimi",
        feature_space=object(),
        taboos=[],
        explored=[],
        cycle_id="c",
    ) == []
