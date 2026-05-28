"""Rainforest Lab — honest multi-agent research framework.

Public API surface for ``import rainforest_lab as rf``. The names re-exported here are the stable
interface; everything else under ``rainforest_lab.*`` is considered internal until promoted."""

from __future__ import annotations

__version__ = "0.1.0"

from rainforest_lab import handoff  # exported as a module: rainforest_lab.handoff.{request,...}
from rainforest_lab.classify import classify
from rainforest_lab.cycle import run_cycle
from rainforest_lab.deliberation import (
    DeliberationConfig,
    ParallelGardenersConfig,
    TreeDeliberation,
    deliberate_tree,
)
from rainforest_lab.domain import (
    AlignRequest,
    DomainData,
    FeatureSpace,
    ResearchDomain,
    Threshold,
)
from rainforest_lab.domains.demo import DemoDomain
from rainforest_lab.dsl.evaluator import compile_node, evaluate
from rainforest_lab.dsl.parser import Node, collect_fields, complexity_tier, max_depth, parse
from rainforest_lab.dsl.random_formula import random_formula
from rainforest_lab.dsl.types import OpDef, OpRegistry
from rainforest_lab.gates.factor_gates import (
    g1_sanity,
    g5_turnover,
    g8_decay,
    g9_liquidity,
    net_sharpe,
)
from rainforest_lab.gates.matched_random import matched_random_threshold
from rainforest_lab.gates.profiles import load_gates_profile
from rainforest_lab.llm.builders import (
    make_llm_aligner,
    make_llm_gardener,
    make_llm_inspector,
    make_llm_skeptic,
)
from rainforest_lab.llm.mocks import MockAligner, MockGardener, MockInspector, MockSkeptic
from rainforest_lab.llm.protocols import (
    Aligner,
    Gardener,
    Inspector,
    Judgment,
    Mechanism,
    Skeptic,
    SkepticVerdict,
)
from rainforest_lab.state import (
    Branch,
    Classification,
    Climate,
    ExecutionMode,
    Forest,
    GateDef,
    GateRecord,
    ResultRecord,
    Seed,
    Tree,
    WeatherEvent,
    latest_cycle_dir,
    load_forest,
    save_forest,
)
from rainforest_lab.trajectories import (
    Trajectory,
    TrajectoryStep,
    compute_reward,
    crossover,
    evolve_seeds_from_archive,
    mutate,
    select_parents,
    synthesize_from_result,
    trajectory_to_seed,
)
from rainforest_lab.validate import ForestValidationError, validate_forest

__all__ = [
    "AlignRequest",
    "Aligner",
    "Branch",
    "Classification",
    "Climate",
    "DeliberationConfig",
    "DemoDomain",
    "DomainData",
    "ExecutionMode",
    "FeatureSpace",
    "Forest",
    "ForestValidationError",
    "Gardener",
    "GateDef",
    "GateRecord",
    "Inspector",
    "Judgment",
    "Mechanism",
    "MockAligner",
    "MockGardener",
    "MockInspector",
    "MockSkeptic",
    "Node",
    "OpDef",
    "OpRegistry",
    "ParallelGardenersConfig",
    "ResearchDomain",
    "ResultRecord",
    "Seed",
    "Skeptic",
    "SkepticVerdict",
    "Threshold",
    "Trajectory",
    "TrajectoryStep",
    "Tree",
    "TreeDeliberation",
    "WeatherEvent",
    "__version__",
    "classify",
    "collect_fields",
    "compile_node",
    "complexity_tier",
    "compute_reward",
    "crossover",
    "deliberate_tree",
    "evaluate",
    "evolve_seeds_from_archive",
    "g1_sanity",
    "g5_turnover",
    "g8_decay",
    "g9_liquidity",
    "handoff",
    "latest_cycle_dir",
    "load_forest",
    "load_gates_profile",
    "make_llm_aligner",
    "make_llm_gardener",
    "make_llm_inspector",
    "make_llm_skeptic",
    "matched_random_threshold",
    "max_depth",
    "mutate",
    "net_sharpe",
    "parse",
    "random_formula",
    "run_cycle",
    "save_forest",
    "select_parents",
    "synthesize_from_result",
    "trajectory_to_seed",
    "validate_forest",
]
