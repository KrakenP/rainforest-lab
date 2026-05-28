from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from rainforest_lab.state import Forest, Seed

DEFAULT_CONFIG_PATH = Path("./configs/rainforest.yaml")
_active_config_path: Path = DEFAULT_CONFIG_PATH

SEED_WEIGHTS: dict[str, float] = {
    "novelty": 0.25,
    "logic_strength": 0.20,
    "option_value": 0.15,
    "cross_tree_potential": 0.15,
    "regime_relevance": 0.10,
    "evidence_hint": 0.10,
    "data_availability": 0.05,
    "validation_cost": -0.15,
    "leakage_risk": -0.20,
    "redundancy": -0.10,
}


def set_config_path(path: Path) -> None:
    """Override the YAML config that drives seed weights + quarantine threshold.

    Useful in tests and for downstream apps that ship a non-default config file."""
    global _active_config_path
    _active_config_path = Path(path)


@dataclass(frozen=True)
class NurseryDecision:
    seed_id: str
    decision: str
    reason: str
    next_validation: str


def score_seed(scores: dict[str, float]) -> float:
    weights = _seed_weights()
    value = sum(float(scores.get(name, 0.0)) * weight for name, weight in weights.items())
    return round(value, 10)


def rank_and_route(
    seeds: list[Seed], *, slots: int, quarantine_threshold: float = 0.8
) -> list[Seed]:
    ranked: list[Seed] = []
    for seed in seeds:
        seed_score = score_seed(seed.scores)
        if float(seed.scores.get("leakage_risk", 0.0)) > quarantine_threshold:
            status = "quarantine"
        else:
            status = "hold"
        ranked.append(seed.model_copy(update={"seed_score": seed_score, "status": status}))

    ranked.sort(
        key=lambda item: (item.status == "quarantine", -(item.seed_score or 0.0), item.seed_id)
    )

    sowed = 0
    routed: list[Seed] = []
    for seed in ranked:
        if seed.status != "quarantine" and sowed < slots:
            routed.append(seed.model_copy(update={"status": "sow_now"}))
            sowed += 1
        elif seed.status != "quarantine":
            routed.append(seed.model_copy(update={"status": "hold"}))
        else:
            routed.append(seed)
    return routed


def nursery_check(seed: Seed, forest: Forest) -> NurseryDecision:
    checks = _nursery_checks(seed, forest)
    reason_prefix = "7 checks: " + ", ".join(checks)

    leakage = float(seed.scores.get("leakage_risk", 0.0))
    data_availability = float(seed.scores.get("data_availability", 0.0))
    redundancy = float(seed.scores.get("redundancy", 0.0))
    novelty = float(seed.scores.get("novelty", 0.0))
    logic_strength = float(seed.scores.get("logic_strength", 0.0))
    validation_cost = float(seed.scores.get("validation_cost", 0.0))

    if leakage > _quarantine_threshold():
        return NurseryDecision(
            seed.seed_id,
            "quarantine",
            f"{reason_prefix}; leakage risk exceeds quarantine threshold",
            "remove leakage path before reuse",
        )
    if not _has_known_tree(seed, forest):
        return NurseryDecision(
            seed.seed_id,
            "hold",
            f"{reason_prefix}; related tree is not in forest",
            "map seed to an active tree",
        )
    if redundancy >= 0.9 or (novelty < 0.25 and redundancy > 0.7):
        return NurseryDecision(
            seed.seed_id,
            "reject",
            f"{reason_prefix}; redundant with existing search space",
            "no validation scheduled",
        )
    if data_availability < 0.3 or _forest_data_not_ready(forest):
        return NurseryDecision(
            seed.seed_id,
            "dormant",
            f"{reason_prefix}; data is not ready",
            "recheck data readiness",
        )
    if not seed.validation_plan.strip() or validation_cost > 0.9:
        return NurseryDecision(
            seed.seed_id,
            "hold",
            f"{reason_prefix}; validation plan is missing or too costly",
            "write a bounded validation plan",
        )
    if logic_strength < 0.2:
        return NurseryDecision(
            seed.seed_id,
            "hold",
            f"{reason_prefix}; logic strength is too weak",
            "tighten mechanism before sowing",
        )
    return NurseryDecision(
        seed.seed_id,
        "sprout",
        f"{reason_prefix}; passes nursery gate",
        seed.validation_plan,
    )


def _nursery_checks(seed: Seed, forest: Forest) -> list[str]:
    return [
        f"leakage={float(seed.scores.get('leakage_risk', 0.0)):.2f}",
        f"data={float(seed.scores.get('data_availability', 0.0)):.2f}",
        f"tree_link={_has_known_tree(seed, forest)}",
        f"novelty={float(seed.scores.get('novelty', 0.0)):.2f}",
        f"logic={float(seed.scores.get('logic_strength', 0.0)):.2f}",
        f"cost={float(seed.scores.get('validation_cost', 0.0)):.2f}",
        f"redundancy={float(seed.scores.get('redundancy', 0.0)):.2f}",
    ]


def _has_known_tree(seed: Seed, forest: Forest) -> bool:
    tree_ids = {tree.tree_id for tree in forest.trees}
    return not seed.related_trees or any(tree_id in tree_ids for tree_id in seed.related_trees)


def _forest_data_not_ready(forest: Forest) -> bool:
    ready = forest.data_soil.get("ready")
    return isinstance(ready, bool) and not ready


def _seed_weights() -> dict[str, float]:
    config = _load_config()
    raw = config.get("seed_scoring_weights", {})
    if isinstance(raw, dict):
        return {key: float(raw.get(key, value)) for key, value in SEED_WEIGHTS.items()}
    return SEED_WEIGHTS


def _quarantine_threshold() -> float:
    config = _load_config()
    policy = config.get("seed_policy", {})
    if isinstance(policy, dict):
        return float(policy.get("quarantine_leakage_threshold", 0.8))
    return 0.8


def _load_config() -> dict[str, Any]:
    if not _active_config_path.exists():
        return {}
    data = yaml.safe_load(_active_config_path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


__all__ = [
    "DEFAULT_CONFIG_PATH",
    "SEED_WEIGHTS",
    "NurseryDecision",
    "nursery_check",
    "rank_and_route",
    "score_seed",
    "set_config_path",
]
