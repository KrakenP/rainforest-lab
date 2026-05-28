from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from rainforest_lab.state import Climate, Forest, Seed, Tree

CONFIG_PATH = Path("./configs/rainforest.yaml")


@dataclass(frozen=True)
class TreeWeather:
    tree_id: str
    weather: str
    allocation: int
    status: str
    freeze_remaining: int
    reason: str


@dataclass(frozen=True)
class ForestWeather:
    cycle: int
    trees: dict[str, TreeWeather]
    trigger_kimi: bool
    trigger_monsoon: bool
    reasoning: list[str]


def route(
    forest: Forest,
    cycle: int,
    *,
    total_fruits: int,
    streaks: dict[str, Any],
    last_alloc: dict[str, Any],
    data_ready: dict[str, bool],
    climate: Climate,
) -> ForestWeather:
    weather_cfg = _weather_config()
    slots_per_cycle = int(weather_cfg["slots_per_cycle"])
    max_tree_slots = max(1, int(slots_per_cycle * climate.max_tree_share))
    trigger_kimi = _forest_no_output(streaks) >= int(
        _exit_config().get("consecutive_dead_cycles", 4)
    )
    trigger_monsoon = cycle > 0 and cycle % int(weather_cfg["monsoon_interval"]) == 0
    reasoning: list[str] = []

    scored: dict[str, TreeWeather] = {}
    for tree in forest.trees:
        event = _classify_tree(
            forest,
            tree,
            cycle,
            total_fruits,
            streaks,
            last_alloc,
            data_ready,
            climate,
            weather_cfg,
            max_tree_slots,
        )
        if event.weather == "thunderstorm":
            trigger_kimi = True
        scored[tree.tree_id] = event

    if trigger_monsoon and scored:
        trigger_kimi = True
        target_id = _first_allocatable(scored) or next(iter(scored))
        current = scored[target_id]
        scored[target_id] = TreeWeather(
            current.tree_id,
            "monsoon",
            max(current.allocation, 1 if current.status == "active" else current.allocation),
            current.status,
            current.freeze_remaining,
            "monsoon interval reached; force Kimi for fresh directions",
        )
        reasoning.append("monsoon interval reached")

    scored = _apply_depth_diversity(scored, forest, climate)
    scored = _apply_flood_diversity_tax(scored, forest, total_fruits, weather_cfg, max_tree_slots)
    scored = _cap_and_normalize(scored, slots_per_cycle, max_tree_slots)

    for tree_id, event in scored.items():
        if not event.reason.strip():
            raise ValueError(f"TreeWeather.reason must be non-empty for {tree_id}")
        reasoning.append(f"{tree_id}: {event.weather} -> {event.allocation}")

    return ForestWeather(
        cycle=cycle,
        trees=scored,
        trigger_kimi=trigger_kimi,
        trigger_monsoon=trigger_monsoon,
        reasoning=reasoning,
    )


def _classify_tree(
    forest: Forest,
    tree: Tree,
    cycle: int,
    total_fruits: int,
    streaks: dict[str, Any],
    last_alloc: dict[str, Any],
    data_ready: dict[str, bool],
    climate: Climate,
    weather_cfg: dict[str, float],
    max_tree_slots: int,
) -> TreeWeather:
    counts = _branch_counts(tree)
    zero_streak = _streak(streaks, tree.tree_id, "zero")
    dead_streak = _streak(streaks, tree.tree_id, "dead")
    freeze_duration = int(weather_cfg["freeze_duration"])
    ready = data_ready.get(tree.tree_id, True)

    if _has_wildfire_warning(forest, tree):
        return _event(
            tree, "wildfire", 0, "frozen", freeze_duration, "sick_leaf warning matches tree"
        )
    if tree.status == "frost":
        interval = int(weather_cfg["frost_recheck_interval"])
        if cycle > 0 and cycle % interval == 0 and ready:
            return _event(tree, "spring", 1, "active", 0, "frost recheck interval found data ready")
        return _event(
            tree,
            "frost",
            0,
            "frost",
            max(1, interval - (cycle % interval)),
            "frost hold until recheck",
        )
    if not ready or bool(tree.weather_priors.get("leakage_risk")):
        return _event(
            tree,
            "frost",
            0,
            "frost",
            int(weather_cfg["frost_recheck_interval"]),
            "data not ready or leakage risk",
        )
    if dead_streak >= int(weather_cfg["thunderstorm_dead_cycles"]) and counts["golden_leaf"] == 0:
        return _event(
            tree,
            "thunderstorm",
            0,
            "frozen",
            freeze_duration,
            "all-dead streak without golden leaves",
        )
    if zero_streak >= int(weather_cfg["heatwave_zero_cycles"]) and counts["golden_leaf"] > 0:
        return _event(
            tree,
            "heatwave",
            0,
            "frozen",
            freeze_duration,
            "zero-fruit streak with golden leaves",
        )
    if counts["golden_leaf"] > 0 and counts["dead_leaf"] > 0 and not bool(
        tree.weather_priors.get("monotone_trend", False)
    ):
        return _event(
            tree,
            "fog",
            1,
            "active",
            0,
            "golden and dead leaves coexist without monotone trend",
        )
    if _has_cross_tree_seed(forest.seeds, tree) or bool(tree.weather_priors.get("cross_tree_seed")):
        return _event(tree, "wind", 1, "active", 0, "high cross-tree-potential seed appeared")
    if _fruit_share(counts["fruit"], total_fruits) > float(weather_cfg["flood_dominance"]):
        return _event(
            tree,
            "flood",
            max(1, max_tree_slots),
            "active",
            0,
            "single tree dominates fruit pool",
        )
    if _is_drought(tree, cycle, last_alloc, weather_cfg):
        return _event(tree, "drought", 1, "active", 0, "neglected tree receives guaranteed slot")
    if _high_moisture(tree, counts):
        return _event(
            tree,
            "heavy_rain",
            max_tree_slots,
            "active",
            0,
            "high moisture and clear next validation",
        )
    if (
        counts["fruit"] > 0
        or counts["golden_leaf"] > 0
        or bool(tree.weather_priors.get("solid_direction"))
    ):
        return _event(
            tree, "rain", 1, "active", 0, "solid direction with neutral-positive evidence"
        )
    return _event(tree, "drizzle", 1, "active", 0, "keep tree alive without deepening")


def _event(
    tree: Tree, weather: str, allocation: int, status: str, freeze_remaining: int, reason: str
) -> TreeWeather:
    return TreeWeather(tree.tree_id, weather, allocation, status, freeze_remaining, reason)


def _apply_depth_diversity(
    events: dict[str, TreeWeather], forest: Forest, climate: Climate
) -> dict[str, TreeWeather]:
    updated = dict(events)
    capped_tree_ids = {
        tree.tree_id
        for tree in forest.trees
        if tree.branches
        and max(branch.depth for branch in tree.branches) >= climate.max_consecutive_depth
    }
    for tree_id in capped_tree_ids:
        event = updated[tree_id]
        if event.allocation > 1:
            updated[tree_id] = TreeWeather(
                event.tree_id,
                event.weather,
                1,
                event.status,
                event.freeze_remaining,
                event.reason + "; depth cap prevents further deepening",
            )
            target_id = _other_active_tree(updated, tree_id)
            if target_id is not None and updated[target_id].allocation == 0:
                target = updated[target_id]
                updated[target_id] = TreeWeather(
                    target.tree_id,
                    target.weather,
                    1,
                    target.status,
                    target.freeze_remaining,
                    target.reason + "; diversity slot forced by depth cap",
                )
    return updated


def _apply_flood_diversity_tax(
    events: dict[str, TreeWeather],
    forest: Forest,
    total_fruits: int,
    weather_cfg: dict[str, float],
    max_tree_slots: int,
) -> dict[str, TreeWeather]:
    updated = dict(events)
    dominant = [
        tree
        for tree in forest.trees
        if _fruit_share(_branch_counts(tree)["fruit"], total_fruits)
        > float(weather_cfg["flood_dominance"])
    ]
    if not dominant:
        return updated
    dominant_ids = {tree.tree_id for tree in dominant}
    target_id = next(
        (
            tree_id
            for tree_id, event in updated.items()
            if tree_id not in dominant_ids and event.status == "active"
        ),
        None,
    )
    if target_id is not None:
        target = updated[target_id]
        updated[target_id] = TreeWeather(
            target.tree_id,
            target.weather,
            max(1, target.allocation),
            target.status,
            target.freeze_remaining,
            target.reason + "; flood diversity tax",
        )
    for tree in dominant:
        event = updated[tree.tree_id]
        updated[tree.tree_id] = TreeWeather(
            event.tree_id,
            event.weather,
            min(event.allocation, max_tree_slots),
            event.status,
            event.freeze_remaining,
            event.reason,
        )
    return updated


def _cap_and_normalize(
    events: dict[str, TreeWeather], slots_per_cycle: int, max_tree_slots: int
) -> dict[str, TreeWeather]:
    capped = {
        tree_id: TreeWeather(
            event.tree_id,
            event.weather,
            min(max(event.allocation, 0), max_tree_slots),
            event.status,
            event.freeze_remaining,
            event.reason,
        )
        for tree_id, event in events.items()
    }
    while sum(event.allocation for event in capped.values()) > slots_per_cycle:
        candidates = [
            event
            for event in capped.values()
            if event.allocation > 0
            and "guaranteed" not in event.reason
            and "diversity tax" not in event.reason
        ]
        if not candidates:
            candidates = [event for event in capped.values() if event.allocation > 0]
        victim = max(candidates, key=lambda event: event.allocation)
        capped[victim.tree_id] = TreeWeather(
            victim.tree_id,
            victim.weather,
            victim.allocation - 1,
            victim.status,
            victim.freeze_remaining,
            victim.reason + "; normalized to slot budget",
        )
    return capped


def _branch_counts(tree: Tree) -> dict[str, int]:
    counts = {"fruit": 0, "golden_leaf": 0, "dead_leaf": 0, "sick_leaf": 0, "normal_leaf": 0}
    for branch in tree.branches:
        if branch.result_classification in counts:
            counts[branch.result_classification] += 1
    return counts


def _fruit_share(fruits: int, total_fruits: int) -> float:
    if total_fruits <= 0:
        return 0.0
    return fruits / total_fruits


def _streak(streaks: dict[str, Any], tree_id: str, name: str) -> int:
    raw = streaks.get(tree_id, {})
    if isinstance(raw, dict):
        for key in (name, f"{name}_streak", f"{name}_cycles"):
            value = raw.get(key)
            if isinstance(value, int):
                return value
    for key in (f"{name}_streak", f"{name}_cycles"):
        raw_map = streaks.get(key, {})
        if isinstance(raw_map, dict):
            value = raw_map.get(tree_id)
            if isinstance(value, int):
                return value
    return 0


def _forest_no_output(streaks: dict[str, Any]) -> int:
    value = streaks.get("_forest_no_output", streaks.get("forest_no_output", 0))
    return value if isinstance(value, int) else 0


def _is_drought(
    tree: Tree, cycle: int, last_alloc: dict[str, Any], weather_cfg: dict[str, float]
) -> bool:
    if tree.recent_budget_share > 0.0:
        return False
    raw = last_alloc.get(tree.tree_id)
    drought_cycles = int(weather_cfg["drought_cycles"])
    if isinstance(raw, int):
        return cycle - raw >= drought_cycles
    if raw is None:
        return False
    return not bool(raw)


def _high_moisture(tree: Tree, counts: dict[str, int]) -> bool:
    moisture = float(tree.weather_priors.get("moisture", 0.0))
    drought = float(tree.weather_priors.get("drought", 0.0))
    clear_next = bool(tree.weather_priors.get("clear_next_validation", False))
    return (moisture >= 0.7 and drought <= 0.3 and clear_next) or counts["fruit"] >= 2


def _has_cross_tree_seed(seeds: list[Seed], tree: Tree) -> bool:
    for seed in seeds:
        if (
            tree.tree_id in seed.related_trees
            and float(seed.scores.get("cross_tree_potential", 0.0)) >= 0.8
        ):
            return True
    return False


def _has_wildfire_warning(forest: Forest, tree: Tree) -> bool:
    if bool(tree.weather_priors.get("sick_leaf_warning")):
        return True
    for warning in forest.sick_leaf_warnings:
        target = warning.get("tree_id") or warning.get("target")
        if target == tree.tree_id:
            return True
    return False


def _first_allocatable(events: dict[str, TreeWeather]) -> str | None:
    for tree_id, event in events.items():
        if event.status == "active":
            return tree_id
    return None


def _other_active_tree(events: dict[str, TreeWeather], tree_id: str) -> str | None:
    for candidate_id, event in events.items():
        if candidate_id != tree_id and event.status == "active":
            return candidate_id
    return None


def _weather_config() -> dict[str, float]:
    config = _load_config().get("weather", {})
    defaults = {
        "slots_per_cycle": 4,
        "heatwave_zero_cycles": 3,
        "thunderstorm_dead_cycles": 3,
        "freeze_duration": 2,
        "flood_dominance": 0.40,
        "drought_cycles": 3,
        "monsoon_interval": 7,
        "frost_recheck_interval": 5,
    }
    if isinstance(config, dict):
        defaults.update({key: float(config.get(key, value)) for key, value in defaults.items()})
    return defaults


def _exit_config() -> dict[str, Any]:
    config = _load_config().get("exit_conditions", {})
    return config if isinstance(config, dict) else {}


def _load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


__all__ = ["ForestWeather", "TreeWeather", "route"]
