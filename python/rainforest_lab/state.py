from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, Field

ExecutionMode = Literal["plan_only", "manual_result", "stub_result", "tool_executed"]
Classification = Literal["fruit", "golden_leaf", "normal_leaf", "dead_leaf", "sick_leaf"]


class Climate(BaseModel):
    mode: str
    temperature: float
    seed_budget: float
    seed_slots: int
    max_tree_share: float
    max_consecutive_depth: int
    novelty_weight: float


class Branch(BaseModel):
    branch_id: str
    parent: str | None = None
    depth: int
    hypothesis: str
    status: Literal["proposed", "sprouting", "executing", "classified", "frozen"]
    cycle_executed: int | None = None
    result_classification: Classification | None = None
    evidence_summary: str = ""
    blocks_reuse: bool = False
    child_branches_proposed: list[str] = Field(default_factory=list)


class Tree(BaseModel):
    tree_id: str
    name: str
    core_logic: str
    status: Literal["active", "dormant", "dead", "frost", "frozen"]
    recent_budget_share: float = 0.0
    max_initial_budget_share: float = 0.18
    branches: list[Branch] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    weather_priors: dict[str, Any] = Field(default_factory=dict)


class Seed(BaseModel):
    seed_id: str
    idea: str
    source_type: str
    related_trees: list[str] = Field(default_factory=list)
    scores: dict[str, float] = Field(default_factory=dict)
    seed_score: float | None = None
    status: Literal["sow_now", "hold", "dormant", "reject", "quarantine"]
    validation_plan: str
    reason: str


class WeatherEvent(BaseModel):
    target: str
    target_type: str
    weather: str
    allocation: float
    reason: str


class GateDef(BaseModel):
    name: str
    hard: bool
    needs_handoff: bool = False


class GateRecord(BaseModel):
    domain: str
    factor_id: str
    gates: dict[str, dict[str, Any]] = Field(default_factory=dict)
    execution_mode: ExecutionMode

    @property
    def complete(self) -> bool:
        return self.is_complete()

    def is_complete(self, gate_spec: list[GateDef] | None = None) -> bool:
        if gate_spec is None:
            return bool(self.gates)

        for gate_def in gate_spec:
            gate = self.gates.get(gate_def.name)
            if gate is None:
                return False
            if gate_def.needs_handoff and not _has_handoff_response(gate):
                return False
        return True


class ResultRecord(BaseModel):
    result_id: str
    task_id: str
    execution_mode: ExecutionMode
    classification: Classification | None = None
    summary: str
    evidence: list[Any] = Field(default_factory=list)
    risks: list[Any] = Field(default_factory=list)
    classification_reason: str
    generated_seeds: list[str] = Field(default_factory=list)
    revival_condition: str = ""
    blocked_from_reuse: bool = False
    gate_record: GateRecord | None = None


class Forest(BaseModel):
    forest_id: str
    cycle_id: str
    research_goal: str
    domain: str
    constraints: list[str] = Field(default_factory=list)
    approval_policy: str
    climate: Climate
    data_soil: dict[str, Any] = Field(default_factory=dict)
    trees: list[Tree] = Field(default_factory=list)
    seeds: list[Seed] = Field(default_factory=list)
    weather_events: list[WeatherEvent] = Field(default_factory=list)
    results: list[ResultRecord] = Field(default_factory=list)
    golden_leaf_pool: list[dict[str, Any]] = Field(default_factory=list)
    sick_leaf_warnings: list[dict[str, Any]] = Field(default_factory=list)
    summary: str


def load_forest(cycle_dir: Path) -> Forest:
    forest_data = _read_yaml(cycle_dir / "forest-state.yaml")
    seed_data = _read_yaml(cycle_dir / "seed-bank.yaml", required=False)
    weather_data = _read_yaml(cycle_dir / "weather-log.yaml", required=False)
    results_data = _read_yaml(cycle_dir / "result-records.yaml", required=False)

    forest_data["seeds"] = seed_data.get("seeds", forest_data.get("seeds", []))
    forest_data["weather_events"] = weather_data.get(
        "weather_events", forest_data.get("weather_events", [])
    )
    forest_data["results"] = results_data.get("results", forest_data.get("results", []))
    return Forest.model_validate(forest_data)


def save_forest(forest: Forest, cycle_dir: Path) -> None:
    cycle_dir.mkdir(parents=True, exist_ok=True)
    data = forest.model_dump(mode="json")

    forest_state = {
        key: value
        for key, value in data.items()
        if key not in {"seeds", "weather_events", "results"}
    }
    seed_bank = {
        "cycle_id": forest.cycle_id,
        "seed_slots": forest.climate.seed_slots,
        "seeds": data["seeds"],
    }
    weather_log = {
        "cycle_id": forest.cycle_id,
        "climate_mode": forest.climate.mode,
        "temperature": forest.climate.temperature,
        "seed_budget": forest.climate.seed_budget,
        "allocations": _allocations_by_target(forest.weather_events),
        "weather_events": data["weather_events"],
    }
    result_records = {"cycle_id": forest.cycle_id, "results": data["results"]}

    _write_yaml(cycle_dir / "forest-state.yaml", forest_state)
    _write_yaml(cycle_dir / "seed-bank.yaml", seed_bank)
    _write_yaml(cycle_dir / "weather-log.yaml", weather_log)
    _write_yaml(cycle_dir / "result-records.yaml", result_records)


def latest_cycle_dir(archive_root: Path) -> Path:
    cycle_dirs = sorted(
        path for path in archive_root.iterdir() if path.is_dir() and path.name.startswith("cycle_")
    )
    if not cycle_dirs:
        raise FileNotFoundError(f"No cycle directories found under {archive_root}")
    return cycle_dirs[-1]


def _read_yaml(path: Path, *, required: bool = True) -> dict[str, Any]:
    if not path.exists():
        if required:
            raise FileNotFoundError(path)
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _allocations_by_target(events: list[WeatherEvent]) -> dict[str, float]:
    allocations: dict[str, float] = {}
    for event in events:
        allocations[event.target] = allocations.get(event.target, 0.0) + event.allocation
    return allocations


def _has_handoff_response(gate: dict[str, Any]) -> bool:
    for key in ("score", "passed", "response", "handoff_response", "judgement", "judgment"):
        if key in gate and gate[key] is not None:
            return True
    return False


__all__ = [
    "Branch",
    "Classification",
    "Climate",
    "ExecutionMode",
    "Forest",
    "GateDef",
    "GateRecord",
    "ResultRecord",
    "Seed",
    "Tree",
    "WeatherEvent",
    "latest_cycle_dir",
    "load_forest",
    "save_forest",
]
