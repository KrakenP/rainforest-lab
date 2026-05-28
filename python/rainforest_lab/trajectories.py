"""Trajectory evolution primitives (rainforest v2.1).

A `Trajectory` is the end-to-end record of one mining run for one candidate factor on one tree:
hypothesis -> (debate) -> inspector -> examiner -> (skeptic challenge) -> aligner -> classify. We
treat trajectories as **first-class evolutionary objects**, archived per cycle (sidecar
``archive/cycle_NNN/trajectories.yaml``) and evolved across cycles via two operators:

- ``mutate(parent)`` localizes the failing step, freezes the prefix, rewrites only that step's
  action via the gardener, and emits a child trajectory whose new hypothesis becomes a seed in the
  next cycle.
- ``crossover(parents)`` synthesizes a child hypothesis from ≥2 healthy parents.

Rigor invariants (extending v2.0 — non-negotiable):

1. Reward is derived from the gate_record, never bestowed. Children start `final_classification =
   None` and must flow through the full gate battery in the next cycle. **No fruit by lineage.**
2. Sick trajectories are poisoned: never selected as parents.
3. trajectory_id is content-addressable (deterministic); selection sorts by reward then id.
4. Single writer: the coordinator owns the trajectory archive; this module reads/builds, never
   mutates forest state.
5. No silent fallback: gardener failures propagate.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from rainforest_lab.state import Classification, ResultRecord, Seed

StepKind = Literal[
    "hypothesis",
    "skeptic_debate",
    "inspector",
    "examiner",
    "skeptic_challenge",
    "aligner",
    "classify",
]
Operation = Literal["genesis", "mutation", "crossover"]


class TrajectoryStep(BaseModel):
    """One step in a mining trajectory. Frozen — steps are reasoned about by content."""

    model_config = ConfigDict(frozen=True)

    step_id: str
    kind: StepKind
    actor_role: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    action: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)


class Trajectory(BaseModel):
    """End-to-end record of one mining run. Frozen — evolution produces NEW trajectories."""

    model_config = ConfigDict(frozen=True)

    trajectory_id: str
    cycle_id: str
    tree_id: str
    parent_ids: list[str] = Field(default_factory=list)
    operation: Operation
    steps: list[TrajectoryStep] = Field(default_factory=list)
    final_classification: Classification | None = None
    reward: float | None = None
    factor_id: str | None = None
    notes: str = ""


_BASE_REWARD: dict[Classification | None, float] = {
    "fruit": 1.0,
    "golden_leaf": 0.5,
    "normal_leaf": 0.2,
    "dead_leaf": 0.0,
    "sick_leaf": -1.0,
    None: 0.0,
}


def compute_reward(traj: Trajectory) -> float:
    """Derive a scalar reward from the trajectory's gate evidence + complexity. Pure function."""

    base = _BASE_REWARD.get(traj.final_classification, 0.0)
    gates_passed = 0
    formula_len = 0
    for step in traj.steps:
        if step.kind == "examiner":
            gates = step.outputs.get("gate_record", {}).get("gates", {}) or {}
            gates_passed = sum(
                1 for gate in gates.values() if isinstance(gate, dict) and gate.get("passed")
            )
        if step.kind == "hypothesis":
            formula_len = len(step.action.get("formula", "") or "")
    return base + 0.05 * gates_passed - 0.001 * formula_len


def select_parents(
    pool: list[Trajectory], k: int, *, exclude_sick: bool = True
) -> list[Trajectory]:
    """Return the top-k trajectories by reward, deterministic tiebreak on trajectory_id."""

    if k <= 0:
        return []
    candidates = [
        t for t in pool if not (exclude_sick and t.final_classification == "sick_leaf")
    ]
    candidates.sort(key=lambda t: (-(t.reward if t.reward is not None else 0.0), t.trajectory_id))
    return candidates[:k]


def synthesize_from_result(
    result: ResultRecord, seed: Seed, *, tree_id: str, cycle_id: str
) -> Trajectory:
    """Build a `genesis` trajectory from one cycle's result + the seed that produced it."""

    steps: list[TrajectoryStep] = [
        TrajectoryStep(
            step_id=f"{result.task_id}_hypothesis",
            kind="hypothesis",
            actor_role="gardener",
            inputs={"seed_id": seed.seed_id},
            action={
                "name": (seed.idea or seed.seed_id)[:64],
                "intuition": seed.idea,
                "formula": seed.validation_plan,
            },
            outputs={
                "mechanism": {
                    "name": (seed.idea or seed.seed_id)[:64],
                    "intuition": seed.idea,
                    "pseudocode": seed.validation_plan,
                }
            },
        )
    ]
    if result.gate_record is not None:
        steps.append(
            TrajectoryStep(
                step_id=f"{result.task_id}_examiner",
                kind="examiner",
                actor_role="examiner",
                inputs={"factor_id": result.gate_record.factor_id},
                action={"evaluation": "ran gate battery"},
                outputs={"gate_record": result.gate_record.model_dump(mode="json")},
            )
        )
    steps.append(
        TrajectoryStep(
            step_id=f"{result.task_id}_classify",
            kind="classify",
            actor_role="coordinator",
            inputs={"task_id": result.task_id},
            action={"classifier": "rainforest result-classification"},
            outputs={
                "classification": result.classification,
                "reason": result.classification_reason,
                "risks": list(result.risks),
            },
        )
    )
    factor_id = result.gate_record.factor_id if result.gate_record is not None else None
    traj = Trajectory(
        trajectory_id=_genesis_id(cycle_id, tree_id, seed.seed_id, factor_id),
        cycle_id=cycle_id,
        tree_id=tree_id,
        parent_ids=[],
        operation="genesis",
        steps=steps,
        final_classification=result.classification,
        factor_id=factor_id,
        notes=f"genesis from seed {seed.seed_id}",
    )
    return traj.model_copy(update={"reward": compute_reward(traj)})


def mutate(
    parent: Trajectory,
    *,
    gardener: Any,
    gardener_model: str,
    feature_space: Any,
    taboos: list[str],
    explored: list[str],
    cycle_id: str,
) -> Trajectory:
    """Localize parent's hypothesis step, freeze the rest, rewrite via the gardener. Hard-fail."""

    if parent.final_classification == "sick_leaf":
        raise ValueError(
            f"cannot mutate sick trajectory {parent.trajectory_id!r} (lookahead must not propagate)"
        )

    hypothesis = _first_step(parent, "hypothesis")
    if hypothesis is None:
        raise ValueError(f"parent trajectory {parent.trajectory_id!r} has no hypothesis step")

    weakness = _extract_weakness(parent)
    domain_logic = (
        f"Refine the parent factor mechanism that failed (or under-performed). "
        f"Parent intuition: {hypothesis.action.get('intuition', '')}. "
        f"Parent formula: {hypothesis.action.get('formula', '')}. "
        f"Address weakness: {weakness or 'unspecified'}. "
        f"Parent gardener model: {gardener_model}."
    )
    revised_list = gardener.mine(domain_logic, feature_space, taboos, explored, 1)
    if not revised_list:
        raise ValueError("gardener returned no revised mechanism (hard fail; no fallback)")
    revised = revised_list[0]

    new_step = TrajectoryStep(
        step_id="hypothesis",
        kind="hypothesis",
        actor_role="gardener",
        inputs={
            "parent_step_id": hypothesis.step_id,
            "parent_trajectory_id": parent.trajectory_id,
            "weakness": weakness,
        },
        action={
            "name": revised.name,
            "intuition": revised.intuition,
            "formula": revised.pseudocode,
        },
        outputs={
            "mechanism": {
                "name": revised.name,
                "intuition": revised.intuition,
                "pseudocode": revised.pseudocode,
            }
        },
    )
    return Trajectory(
        trajectory_id=_mutation_id(parent.trajectory_id, new_step.action),
        cycle_id=cycle_id,
        tree_id=parent.tree_id,
        parent_ids=[parent.trajectory_id],
        operation="mutation",
        steps=[new_step],
        final_classification=None,
        reward=None,
        factor_id=None,
        notes=(
            f"mutation of {parent.trajectory_id} at hypothesis step; "
            f"weakness={weakness or 'unspecified'}"
        ),
    )


def crossover(
    parents: list[Trajectory],
    *,
    gardener: Any,
    gardener_model: str,
    feature_space: Any,
    taboos: list[str],
    explored: list[str],
    cycle_id: str,
) -> Trajectory:
    """Recombine ≥2 healthy parents' hypotheses into a child via the gardener. Hard-fail."""

    healthy = [p for p in parents if p.final_classification != "sick_leaf"]
    if len(healthy) < 2:
        raise ValueError(
            f"crossover requires at least 2 healthy parents (got {len(healthy)} non-sick "
            f"out of {len(parents)})"
        )
    hypotheses = [_first_step(p, "hypothesis") for p in healthy]
    if any(h is None for h in hypotheses):
        raise ValueError("all crossover parents must have a hypothesis step")

    intuitions = "; ".join(
        h.action.get("intuition", "") for h in hypotheses if h is not None    )
    formulas = "; ".join(
        h.action.get("formula", "") for h in hypotheses if h is not None    )
    domain_logic = (
        f"Recombine the best ideas from these parent mechanisms into a single child mechanism. "
        f"Parent intuitions: {intuitions}. Parent formulas: {formulas}. "
        f"Produce a synthesized mechanism that inherits the strongest signals. "
        f"Parent gardener model: {gardener_model}."
    )
    synthesized_list = gardener.mine(domain_logic, feature_space, taboos, explored, 1)
    if not synthesized_list:
        raise ValueError("gardener returned no synthesized mechanism (hard fail; no fallback)")
    synthesized = synthesized_list[0]

    new_step = TrajectoryStep(
        step_id="hypothesis",
        kind="hypothesis",
        actor_role="gardener",
        inputs={"parent_trajectory_ids": [p.trajectory_id for p in healthy]},
        action={
            "name": synthesized.name,
            "intuition": synthesized.intuition,
            "formula": synthesized.pseudocode,
        },
        outputs={
            "mechanism": {
                "name": synthesized.name,
                "intuition": synthesized.intuition,
                "pseudocode": synthesized.pseudocode,
            }
        },
    )
    parent_ids = sorted(p.trajectory_id for p in healthy)
    best = max(healthy, key=lambda p: p.reward if p.reward is not None else 0.0)
    return Trajectory(
        trajectory_id=_crossover_id(parent_ids, new_step.action),
        cycle_id=cycle_id,
        tree_id=best.tree_id,
        parent_ids=parent_ids,
        operation="crossover",
        steps=[new_step],
        final_classification=None,
        reward=None,
        factor_id=None,
        notes=f"crossover of {len(healthy)} parents on tree {best.tree_id}",
    )


def trajectory_to_seed(
    traj: Trajectory, *, cycle_id: str, related_trees: list[str] | None = None
) -> Seed:
    """Convert an evolved child trajectory into a rainforest Seed for the next cycle."""

    hypothesis = _first_step(traj, "hypothesis")
    if hypothesis is None:
        raise ValueError(f"trajectory {traj.trajectory_id!r} has no hypothesis step")
    formula = (hypothesis.action.get("formula") or "").strip()
    if not formula:
        raise ValueError(f"hypothesis step of {traj.trajectory_id!r} has no formula")

    source_type = {
        "mutation": "trajectory_mutation",
        "crossover": "trajectory_crossover",
        "genesis": "trajectory_genesis",
    }[traj.operation]
    cross_tree = 0.6 if len(traj.parent_ids) > 1 else 0.3
    scores = {
        "novelty": 0.70,
        "logic_strength": 0.70,
        "option_value": 0.60,
        "cross_tree_potential": cross_tree,
        "regime_relevance": 0.50,
        "evidence_hint": 0.50,
        "data_availability": 1.00,
        "validation_cost": 0.30,
        "leakage_risk": 0.00,
        "redundancy": 0.10,
    }
    return Seed(
        seed_id=f"seed_{cycle_id}_{traj.trajectory_id}",
        idea=hypothesis.action.get("intuition") or "evolved candidate",
        source_type=source_type,
        related_trees=related_trees or [traj.tree_id],
        scores=scores,
        status="hold",
        validation_plan=formula,
        reason=(
            f"evolved from {','.join(traj.parent_ids) or 'genesis'} via {traj.operation}"
        ),
    )


def evolve_seeds_from_archive(
    prev_cycle_dir: Path,
    *,
    k_mut: int,
    k_xover: int,
    gardener: Any,
    gardener_model: str,
    feature_space: Any,
    taboos: list[str],
    explored: list[str],
    cycle_id: str,
    xover_parents: int = 2,
) -> list[Seed]:
    """Load prev archive trajectories, evolve them, and return ready-to-inject Seeds.

    This is the integration helper that the coordinator can call at the start of a cycle. It does
    NOT mutate any forest state; it returns a list[Seed] that the caller appends to the next
    forest's seeds. The cycle then evaluates them through the unchanged gate battery — no fruit by
    lineage.
    """

    pool = load_trajectories(prev_cycle_dir)
    if not pool:
        return []
    seeds: list[Seed] = []
    for parent in select_parents(pool, k_mut, exclude_sick=True):
        child = mutate(
            parent,
            gardener=gardener,
            gardener_model=gardener_model,
            feature_space=feature_space,
            taboos=taboos,
            explored=explored,
            cycle_id=cycle_id,
        )
        seeds.append(trajectory_to_seed(child, cycle_id=cycle_id))
    xover_pool = select_parents(pool, k_xover * xover_parents, exclude_sick=True)
    for start in range(0, len(xover_pool) - xover_parents + 1, xover_parents):
        group = xover_pool[start : start + xover_parents]
        if len(group) < 2:
            break
        child = crossover(
            group,
            gardener=gardener,
            gardener_model=gardener_model,
            feature_space=feature_space,
            taboos=taboos,
            explored=explored,
            cycle_id=cycle_id,
        )
        seeds.append(trajectory_to_seed(child, cycle_id=cycle_id))
    return seeds


def load_trajectories(cycle_dir: Path) -> list[Trajectory]:
    path = cycle_dir / "trajectories.yaml"
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not data:
        return []
    raw_list = data.get("trajectories") if isinstance(data, dict) else None
    if not isinstance(raw_list, list):
        return []
    return [Trajectory.model_validate(item) for item in raw_list]


def save_trajectories(trajectories: list[Trajectory], cycle_dir: Path) -> None:
    cycle_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "cycle_dir": str(cycle_dir),
        "trajectories": [t.model_dump(mode="json") for t in trajectories],
    }
    (cycle_dir / "trajectories.yaml").write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )


def _first_step(traj: Trajectory, kind: StepKind) -> TrajectoryStep | None:
    for step in traj.steps:
        if step.kind == kind:
            return step
    return None


def _extract_weakness(traj: Trajectory) -> str:
    """Pull a free-text weakness signal from recorded skeptic / classify outputs (best effort)."""

    for step in traj.steps:
        if step.kind in {"skeptic_challenge", "skeptic_debate"}:
            risks = step.outputs.get("risks") or step.outputs.get("verdict") or {}
            if isinstance(risks, list) and risks:
                return "; ".join(str(item) for item in risks if item)
            if isinstance(risks, dict):
                concerns = risks.get("weaknesses") or risks.get("concerns")
                if isinstance(concerns, list) and concerns:
                    return "; ".join(str(item) for item in concerns)
        if step.kind == "classify":
            risks = step.outputs.get("risks") or []
            if isinstance(risks, list) and risks:
                return "; ".join(str(item) for item in risks)
            reason = step.outputs.get("reason")
            if isinstance(reason, str) and reason.strip():
                return reason
    return ""


def _genesis_id(cycle_id: str, tree_id: str, seed_id: str, factor_id: str | None) -> str:
    content = f"{cycle_id}|{tree_id}|{seed_id}|{factor_id or ''}"
    return "traj_gen_" + hashlib.sha1(content.encode()).hexdigest()[:8]


def _mutation_id(parent_id: str, new_action: dict[str, Any]) -> str:
    content = parent_id + "|" + json.dumps(new_action, sort_keys=True)
    return "traj_mut_" + hashlib.sha1(content.encode()).hexdigest()[:8]


def _crossover_id(parent_ids: list[str], new_action: dict[str, Any]) -> str:
    content = ",".join(parent_ids) + "|" + json.dumps(new_action, sort_keys=True)
    return "traj_xover_" + hashlib.sha1(content.encode()).hexdigest()[:8]


__all__ = [
    "Operation",
    "StepKind",
    "Trajectory",
    "TrajectoryStep",
    "compute_reward",
    "crossover",
    "evolve_seeds_from_archive",
    "load_trajectories",
    "mutate",
    "save_trajectories",
    "select_parents",
    "synthesize_from_result",
    "trajectory_to_seed",
]
