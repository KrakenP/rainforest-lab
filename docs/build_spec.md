# Rainforest Lab Build Spec

> A seeded, weather-guided research framework for AI agents.  
> 面向 AI coding agent 的系统构建说明文档。

---

## 0. Purpose

Rainforest Lab is a framework for managing open-ended AI research.

It helps an AI agent avoid over-focusing on a single promising direction by organizing research into a forest of directions, allocating research attention through a weather system, and creating new directions through a seed system.

This document is written for an AI coding agent that will start building the system from scratch.

The first implementation should be a minimal but extensible research framework, not a full production trading platform.

---

## 1. Product Definition

### 1.1 Project Name

```text
Rainforest Lab
```

### 1.2 One-line Description

```text
A seeded, weather-guided research framework for AI agents.
```

### 1.3 Core Concept

Rainforest Lab treats research as an evolving forest:

- Research directions are trees.
- Hypotheses are branches.
- Successful validated results are fruits.
- Failed experiments are leaves.
- Valuable failures are golden leaves.
- New potential directions are seeds.
- Low-cost validation happens in a nursery.
- The weather system allocates attention and research budget.
- The forest grounding stage initializes the environment through user-guided brainstorming.

### 1.4 Primary Goal

Build a system that helps AI agents:

1. Maintain multiple research directions.
2. Dynamically allocate research attention.
3. Avoid over-digging one direction.
4. Preserve useful failures.
5. Generate and validate new research seeds.
6. Keep research memory structured and reusable.
7. Support quantitative research first, while remaining general enough for other research domains.

---

## 2. MVP Scope

The first version should focus on a local, file-based framework that can run without cloud infrastructure.

### 2.1 Must Build in MVP

Build these modules first:

1. Forest Grounding
2. Tree Registry
3. Seed System
4. Nursery
5. Weather Router
6. Research Task Planner
7. Result Classifier
8. Archive / Memory Store
9. Basic CLI
10. Config files
11. Unit tests

### 2.2 Do Not Build in MVP

Avoid these in the first version:

- Real brokerage integration
- Live trading
- Complex UI
- Distributed execution
- Full web app
- Vector database dependency
- Heavy workflow engine
- Automatic use of paid APIs by default
- Any claim that the system can generate profitable strategies

### 2.3 MVP Philosophy

The MVP should prove the research orchestration loop:

```text
User intent
→ Forest grounding
→ Initial trees and seeds
→ Weather allocation
→ Research tasks
→ Experiment results
→ Fruit / leaf classification
→ Memory update
→ Next cycle
```

The first version can use mock experiments or simple user-provided results. It does not need to implement a full backtesting engine internally.

---

## 3. Recommended Tech Stack

Use a simple Python-first stack.

```text
Language: Python 3.11+
Config: YAML
Storage: SQLite + local JSON/Markdown files
CLI: Typer or Click
Validation: Pydantic
Testing: pytest
Formatting: ruff + black
Optional notebooks: Jupyter
```

Recommended package layout:

```text
rainforest_lab/
  __init__.py
  cli.py
  config/
  core/
  grounding/
  forest/
  seeds/
  weather/
  nursery/
  research/
  archive/
  shared_experts/
  utils/

tests/
examples/
docs/
configs/
prompts/
```

---

## 4. Directory Structure

Create this structure:

```text
rainforest-lab/
├── README.md
├── pyproject.toml
├── configs/
│   ├── default.yaml
│   ├── quant_a_share.yaml
│   └── research_generic.yaml
├── docs/
│   ├── concept.md
│   ├── build_spec.md
│   ├── weather_system.md
│   ├── seed_system.md
│   ├── forest_grounding.md
│   └── examples.md
├── prompts/
│   ├── forest_grounding.md
│   ├── seed_generation.md
│   ├── tree_research.md
│   └── result_classification.md
├── examples/
│   ├── quant_mock_cycle/
│   └── generic_research_cycle/
├── rainforest_lab/
│   ├── __init__.py
│   ├── cli.py
│   ├── core/
│   │   ├── models.py
│   │   ├── enums.py
│   │   └── scoring.py
│   ├── grounding/
│   │   ├── interview.py
│   │   ├── mapper.py
│   │   └── templates.py
│   ├── forest/
│   │   ├── manager.py
│   │   ├── registry.py
│   │   └── profiles.py
│   ├── seeds/
│   │   ├── generator.py
│   │   ├── router.py
│   │   └── bank.py
│   ├── nursery/
│   │   ├── validator.py
│   │   └── promotion.py
│   ├── weather/
│   │   ├── router.py
│   │   ├── climate.py
│   │   └── allocation.py
│   ├── research/
│   │   ├── planner.py
│   │   ├── task.py
│   │   └── executor_stub.py
│   ├── archive/
│   │   ├── store.py
│   │   ├── sqlite_store.py
│   │   └── markdown_exporter.py
│   ├── shared_experts/
│   │   ├── base.py
│   │   ├── leakage.py
│   │   ├── cost.py
│   │   ├── correlation.py
│   │   └── robustness.py
│   └── utils/
│       ├── ids.py
│       ├── time.py
│       └── yaml_io.py
└── tests/
    ├── test_grounding.py
    ├── test_weather_router.py
    ├── test_seed_router.py
    ├── test_nursery.py
    └── test_archive.py
```

---

## 5. Core Domain Model

Use Pydantic models for all core objects.

### 5.1 Enums

Create these enums in `core/enums.py`:

```python
from enum import Enum


class TreeStatus(str, Enum):
    SAPLING = "sapling"
    YOUNG = "young"
    MATURE = "mature"
    DORMANT = "dormant"
    PRUNED = "pruned"


class SeedStatus(str, Enum):
    ACTIVE = "active"
    DORMANT = "dormant"
    REJECTED = "rejected"
    PROMOTED = "promoted"


class SeedSourceType(str, Enum):
    GENESIS = "genesis"
    GOLDEN_LEAF = "golden_leaf"
    CROSS_TREE = "cross_tree"
    REGIME = "regime"
    DATA_SOURCE = "data_source"
    COUNTERFACTUAL = "counterfactual"
    EXTERNAL = "external"
    RANDOM = "random"


class ResultType(str, Enum):
    FRUIT = "fruit"
    GOLDEN_LEAF = "golden_leaf"
    NORMAL_LEAF = "normal_leaf"
    DEAD_LEAF = "dead_leaf"
    SICK_LEAF = "sick_leaf"


class ClimateMode(str, Enum):
    EXPLORATION = "exploration"
    BALANCED = "balanced"
    HARVEST = "harvest"
    RESTORATION = "restoration"
    DIVERSIFICATION = "diversification"
    CRISIS = "crisis"


class WeatherType(str, Enum):
    DRIZZLE = "drizzle"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    DROUGHT = "drought"
    WIND = "wind"
    THUNDERSTORM = "thunderstorm"
    FOG = "fog"
    FROST = "frost"
    HEATWAVE = "heatwave"
    TYPHOON = "typhoon"
```

---

### 5.2 Environment Profile

Create in `core/models.py`:

```python
from pydantic import BaseModel, Field
from typing import Any, Optional
from .enums import ClimateMode


class MarketProfile(BaseModel):
    name: str
    asset_class: str = "unknown"
    universe: Optional[str] = None
    benchmark: Optional[str] = None
    rebalance_preference: Optional[str] = None


class TerrainProfile(BaseModel):
    constraints: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class DataSoilProfile(BaseModel):
    price_volume: float = 0.0
    fundamentals: float = 0.0
    analyst_forecast: float = 0.0
    fund_flow: float = 0.0
    news_text: float = 0.0
    alternative_data: float = 0.0
    microstructure: float = 0.0
    macro: float = 0.0


class RegimeProfile(BaseModel):
    trend_strength: float = 0.5
    volatility_level: float = 0.5
    turnover_level: float = 0.5
    style_rotation: float = 0.5
    risk_appetite: float = 0.5
    policy_intensity: float = 0.5
    liquidity_condition: float = 0.5


class ClimateConfig(BaseModel):
    mode: ClimateMode = ClimateMode.EXPLORATION
    temperature: float = 1.2
    min_rainfall: float = 0.15
    seed_budget: float = 0.20
    max_tree_share: float = 0.30
    max_consecutive_depth: int = 2
    novelty_weight: float = 0.35
    balance_lambda: float = 0.25
    overfit_penalty: float = 0.50
    shared_expert_strictness: float = 0.50


class EnvironmentProfile(BaseModel):
    market: MarketProfile
    terrain: TerrainProfile = Field(default_factory=TerrainProfile)
    data_soil: DataSoilProfile = Field(default_factory=DataSoilProfile)
    current_regime: RegimeProfile = Field(default_factory=RegimeProfile)
    climate: ClimateConfig = Field(default_factory=ClimateConfig)
```

---

### 5.3 Tree Profile

```python
from pydantic import BaseModel, Field
from typing import Optional
from .enums import TreeStatus


class TreePriors(BaseModel):
    terrain_fit: float = 0.5
    regime_fit: float = 0.5
    data_readiness: float = 0.5
    logic_strength: float = 0.5
    novelty_potential: float = 0.5
    cross_pollination_potential: float = 0.5


class TreeSoil(BaseModel):
    data_quality: float = 0.5
    latency_risk: float = 0.5
    transaction_cost_risk: float = 0.5
    capacity_limit: float = 0.5
    leakage_risk: float = 0.5


class TreeWeatherState(BaseModel):
    moisture: float = 0.5
    drought_need: float = 0.0
    attention_prior: float = 0.0
    recent_budget_share: float = 0.0
    recent_success_rate: float = 0.0
    dormancy: float = 0.0
    overdigging: float = 0.0
    redundancy: float = 0.0
    overfit_risk: float = 0.0
    golden_leaf_density: float = 0.0


class TreeProfile(BaseModel):
    tree_id: str
    name: str
    core_logic: str
    status: TreeStatus = TreeStatus.MATURE
    priors: TreePriors = Field(default_factory=TreePriors)
    soil: TreeSoil = Field(default_factory=TreeSoil)
    weather: TreeWeatherState = Field(default_factory=TreeWeatherState)
    max_initial_budget_share: float = 0.18
    max_consecutive_depth: int = 2
    notes: list[str] = Field(default_factory=list)
```

---

### 5.4 Seed Model

```python
from pydantic import BaseModel, Field
from typing import Optional
from .enums import SeedSourceType, SeedStatus


class Seed(BaseModel):
    seed_id: str
    source_type: SeedSourceType
    idea: str
    related_trees: list[str] = Field(default_factory=list)
    financial_logic: Optional[str] = None
    data_requirement: list[str] = Field(default_factory=list)
    validation_plan: Optional[str] = None
    novelty_score: float = 0.5
    logic_strength: float = 0.5
    data_availability: float = 0.5
    regime_relevance: float = 0.5
    cross_tree_potential: float = 0.5
    validation_cost: float = 0.5
    leakage_risk: float = 0.5
    status: SeedStatus = SeedStatus.ACTIVE
    priority: float = 0.5
    notes: list[str] = Field(default_factory=list)
```

---

### 5.5 Experiment and Result Model

```python
from pydantic import BaseModel, Field
from typing import Any, Optional
from .enums import ResultType


class ResearchTask(BaseModel):
    task_id: str
    tree_id: str | None = None
    seed_id: str | None = None
    title: str
    hypothesis: str
    research_mode: str
    budget: float
    validation_plan: str
    expected_output: str = "experiment_result"


class ExperimentResult(BaseModel):
    experiment_id: str
    task_id: str
    tree_id: str | None = None
    seed_id: str | None = None
    hypothesis: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    summary: str = ""
    risks: list[str] = Field(default_factory=list)
    result_type: ResultType | None = None
    classification_reason: Optional[str] = None
    revival_condition: Optional[str] = None
    generated_seed_ideas: list[str] = Field(default_factory=list)
```

---

## 6. Forest Grounding

Forest Grounding is the initialization phase.

It replaces the term “Genesis Interview”.

### 6.1 Purpose

Forest Grounding converts user-friendly research intent into executable environment variables.

The user should not need to directly set abstract parameters such as temperature, moisture, soil penalty, rainfall, or drought.

Instead, the system asks normal questions and maps answers to configuration.

### 6.2 User-facing Questions

Implement a guided interview with these questions:

1. What is your research goal?
2. What market or domain are you studying?
3. What data do you have?
4. What are your cost, frequency, or implementation constraints?
5. Which mistake are you most worried about?
6. Which directions do you want to emphasize?
7. Which directions should be avoided or deprioritized?
8. How much should the AI ask for approval?

### 6.3 Mapping Rules

Implement mapping rules in `grounding/mapper.py`.

#### Research Goal Mapping

```text
Broad exploration
→ climate_mode = exploration
→ temperature high
→ seed_budget high
→ max_tree_share low
→ novelty_weight high

Filter existing ideas
→ climate_mode = balanced
→ temperature medium
→ seed_budget medium
→ robustness medium

Validate candidates
→ climate_mode = harvest
→ temperature low
→ seed_budget low
→ robustness high
→ shared expert strictness high

Repair unstable results
→ climate_mode = restoration
→ overfit_penalty high
→ audit budget high
→ sick leaf sensitivity high
```

#### Mistake Fear Mapping

```text
Fear missing new directions
→ seed_budget up
→ novelty_weight up
→ germination_threshold down

Fear overfitting
→ overfit_penalty up
→ promotion_threshold up
→ shared_expert_strictness up

Fear research too scattered
→ top_k down
→ seed_slots down
→ max_tree_share up

Fear drilling one direction too deeply
→ min_rainfall up
→ max_tree_share down
→ max_consecutive_depth down

Fear non-tradable results
→ transaction_cost_weight up
→ capacity_weight up
→ turnover_penalty up
```

### 6.4 Output Files

Forest Grounding should generate:

```text
configs/environment.generated.yaml
configs/tree_profiles.generated.yaml
configs/genesis_seeds.generated.yaml
```

### 6.5 Human-readable Summary

After grounding, generate a plain-language summary:

```text
Your forest will start in exploration mode.
The system will allocate more attention to seeds and cold directions.
Fund flow and industry rotation receive a small initial boost.
News sentiment is set to dormant due to data constraints.
The system will prevent any single tree from using more than 30% of early research budget.
```

---

## 7. Weather System

The Weather System is the attention and research budget scheduler.

### 7.1 Weather Variables

Use these system-level concepts:

| Concept | Meaning |
|---|---|
| Moisture | How much a tree deserves attention now |
| Drought Need | Whether a tree is overused or risky |
| Temperature | Exploration entropy |
| Rainfall | Research budget allocation |
| Wind | Cross-tree attention shift or regime revaluation |
| Cloud Density | Accumulated untested hypotheses |
| Humidity | Latent clue density |
| Heatwave | Overfitting or excessive excitement |
| Fog | Low confidence due to unclear evidence |
| Frost | Risk freeze |

### 7.2 Tree Moisture Formula

Implement in `core/scoring.py`:

```text
Moisture_i =
  m1 * RegimeFit_i
+ m2 * GoldenLeafDensity_i
+ m3 * Dormancy_i
+ m4 * Uncertainty_i
+ m5 * NoveltyPotential_i
+ m6 * DataReadiness_i
+ m7 * CrossPollinationPotential_i
- n1 * RecentBudgetShare_i
- n2 * Redundancy_i
- n3 * OverfitRisk_i
- n4 * SoilPenalty_i
- n5 * CostPenalty_i
```

Use a simple default weighted average first. Make weights configurable.

### 7.3 Drought Need Formula

```text
DroughtNeed_i =
  v1 * Overdigging_i
+ v2 * Redundancy_i
+ v3 * MarginalReturnDecay_i
+ v4 * OverfitRisk_i
+ v5 * Crowding_i
+ v6 * SamePatternGeneration_i
```

MVP can approximate unavailable fields with 0.0 and gradually improve.

### 7.4 Attention Allocation

Convert tree scores into allocation:

```text
Attention_i = softmax(Moisture_i / Temperature)
```

Then apply constraints:

1. Enforce `min_rainfall`.
2. Enforce `max_tree_share`.
3. Penalize high `drought_need`.
4. Reserve `seed_budget` for seeds.
5. Reserve optional budget for golden leaf revival.
6. Normalize to 1.0.

### 7.5 Weather Decision

For each tree:

```text
High moisture + low drought → rain or heavy rain
Medium moisture → drizzle or rain
Low moisture + high dormancy → drizzle
High moisture + high drought → heatwave or drought
High fog signals → fog
High risk signals → frost
Regime shift → wind
System-level low novelty → thunderstorm
```

### 7.6 Weather Log

Every cycle must produce a weather log:

```yaml
cycle_id: cycle_001
climate_mode: exploration
temperature: 1.2
allocations:
  fund_flow: 0.18
  industry_rotation: 0.16
  fundamentals: 0.11
seed_budget: 0.20
weather_events:
  - tree_id: fund_flow
    weather: rain
    reason: high regime fit and user interest, but capped by max_tree_share
  - tree_id: news_sentiment
    weather: drizzle
    reason: dormant due to data constraints
```

---

## 8. Seed System

The Seed System creates new research directions.

### 8.1 Seed Types

Implement generation support for:

1. Genesis seeds
2. Golden leaf seeds
3. Cross-tree seeds
4. Regime seeds
5. Data source seeds
6. Counterfactual seeds
7. External knowledge seeds
8. Random mutation seeds

### 8.2 Seed Score

Implement in `seeds/router.py`:

```text
SeedScore_j =
  a1 * Novelty_j
+ a2 * LogicStrength_j
+ a3 * RegimeRelevance_j
+ a4 * CrossTreePotential_j
+ a5 * DataAvailability_j
+ a6 * FailureInsight_j
- b1 * ValidationCost_j
- b2 * Redundancy_j
- b3 * SpeculationRisk_j
- b4 * LeakageRisk_j
```

### 8.3 Seed Routing

Rules:

```text
SeedScore >= germination_threshold
→ active seed, send to nursery

Medium score with future value
→ dormant seed bank

Low score or high leakage risk
→ rejected archive
```

### 8.4 Bias Guard

If user strongly favors a tree, generate counterfactual seeds for it.

Example:

```text
User favors fund flow.
Generate:
- When is fund inflow actually distribution?
- When does fund flow fail due to high turnover?
- Which industries show false fund flow signals?
```

---

## 9. Nursery

The Nursery is a low-cost validation layer for seeds.

### 9.1 Nursery Checks

Implement these checks:

1. Is the hypothesis clear?
2. Is required data available?
3. Is there obvious leakage risk?
4. Is it redundant with existing trees?
5. Can it be validated cheaply?
6. Is there at least one plausible local validity condition?
7. Does it have a basic research plan?

### 9.2 Promotion Stages

```text
Seed → Sprout → Sapling → Young Tree → Mature Tree
```

MVP should implement:

```text
Seed → Sprout → Sapling
```

Later versions can implement Young Tree and Mature Tree promotion.

### 9.3 Promotion Conditions

Seed to Sprout:

```text
clear hypothesis
available data
not obviously leaking
not fully redundant
```

Sprout to Sapling:

```text
some early evidence
clear next validation plan
not pure speculation
```

---

## 10. Research Task Planner

The task planner converts weather allocation into research tasks.

### 10.1 Task Sources

Tasks can come from:

- Active trees
- Active seeds
- Golden leaves
- Counterfactual checks
- Weather-triggered revaluation
- User-requested directions

### 10.2 Task Types

```text
explore_tree
validate_seed
revive_golden_leaf
counterfactual_test
cross_tree_pollination
robustness_check
prune_tree
summarize_memory
```

### 10.3 Task Output

Each task should include:

```yaml
task_id: task_001
type: validate_seed
tree_id: fund_flow
seed_id: seed_003
hypothesis: "High turnover weakens fund flow continuation."
budget: 0.05
validation_plan: "Run simple grouped backtest or request external evaluator."
expected_output: experiment_result
```

---

## 11. Result Classification

Classify every result.

### 11.1 Fruit

A result becomes Fruit if:

```text
It passes initial validation.
It is not obviously leaking.
It has useful signal or research value.
It is not highly redundant.
It has a next-step validation path.
```

For quant research, Fruit does not mean tradable. It means research candidate.

### 11.2 Golden Leaf

A failed result becomes Golden Leaf if:

```text
It fails overall but works in a sub-regime.
It reveals a boundary condition.
It is low-correlation but weak.
It suggests a new seed.
It explains why a tree fails.
It can become valuable under future conditions.
```

### 11.3 Dead Leaf

Dead Leaf means:

```text
Weak logic.
Weak evidence.
No useful boundary.
Low revival value.
```

### 11.4 Sick Leaf

Sick Leaf means:

```text
Data leakage.
Future function.
Overfit pattern.
Invalid data handling.
Non-tradable artifact.
Spurious relationship.
```

Sick Leaves should be archived as warnings and should not be reused.

---

## 12. Archive and Memory Store

Use SQLite as the default local database.

### 12.1 Tables

Implement these tables:

```sql
CREATE TABLE trees (
    tree_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    core_logic TEXT,
    status TEXT,
    profile_json TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE seeds (
    seed_id TEXT PRIMARY KEY,
    source_type TEXT,
    idea TEXT NOT NULL,
    status TEXT,
    related_trees_json TEXT,
    score REAL,
    seed_json TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE tasks (
    task_id TEXT PRIMARY KEY,
    task_type TEXT,
    tree_id TEXT,
    seed_id TEXT,
    title TEXT,
    hypothesis TEXT,
    budget REAL,
    task_json TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE experiment_results (
    experiment_id TEXT PRIMARY KEY,
    task_id TEXT,
    tree_id TEXT,
    seed_id TEXT,
    hypothesis TEXT,
    result_type TEXT,
    summary TEXT,
    metrics_json TEXT,
    result_json TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE weather_logs (
    cycle_id TEXT PRIMARY KEY,
    climate_mode TEXT,
    temperature REAL,
    allocation_json TEXT,
    weather_events_json TEXT,
    created_at TEXT
);
```

### 12.2 Markdown Export

Implement export commands:

```text
rainforest export forest
rainforest export seeds
rainforest export weather-log
rainforest export report
```

Exports should write Markdown reports to `outputs/`.

---

## 13. CLI Design

Implement a CLI entrypoint named `rainforest`.

### 13.1 Commands

```text
rainforest init
rainforest ground
rainforest show forest
rainforest show seeds
rainforest cycle plan
rainforest cycle run-stub
rainforest result add
rainforest export report
```

### 13.2 Example Workflow

```bash
rainforest init --project my-alpha-forest
cd my-alpha-forest
rainforest ground
rainforest show forest
rainforest cycle plan
rainforest cycle run-stub
rainforest export report
```

### 13.3 `rainforest ground`

Should run Forest Grounding questions and generate configs.

### 13.4 `rainforest cycle plan`

Should:

1. Load environment config.
2. Load tree profiles.
3. Load seeds.
4. Run weather router.
5. Generate research tasks.
6. Write a cycle plan.

### 13.5 `rainforest cycle run-stub`

For MVP, this can generate mock results or ask the user to manually input results.

Do not pretend to run real research unless an executor exists.

---

## 14. LLM Prompt Files

Create prompt templates as Markdown files.

### 14.1 `prompts/forest_grounding.md`

```markdown
You are the Forest Grounding Agent for Rainforest Lab.

Your task is to convert a user's natural-language research intent into an initial research forest configuration.

Do not ask the user to set abstract parameters such as temperature, moisture, drought, soil penalty, or rainfall.
Ask user-friendly questions about goals, market, data, constraints, fears, preferred directions, avoided directions, and approval style.

Then output:
1. Environment profile
2. Initial climate
3. Initial tree profiles
4. Initial seeds
5. Bias guard rules
6. Human-readable summary
```

### 14.2 `prompts/seed_generation.md`

```markdown
You are the Seed Generator for Rainforest Lab.

Generate research seeds from:
- Golden leaves
- Cross-tree combinations
- Regime changes
- Data sources
- Counterfactual reasoning
- External knowledge
- Controlled mutation

Each seed must include:
- idea
- source_type
- related_trees
- logic
- data requirement
- validation plan
- novelty estimate
- risk estimate
```

### 14.3 `prompts/result_classification.md`

```markdown
You are the Result Classifier for Rainforest Lab.

Classify an experiment result as:
- Fruit
- Golden Leaf
- Normal Leaf
- Dead Leaf
- Sick Leaf

Explain:
- Why this label fits
- Whether this result should generate new seeds
- Whether it has a revival condition
- Whether it should be blocked from reuse
- Which tree memory should be updated
```

---

## 15. Example Default Config

Create `configs/default.yaml`:

```yaml
project:
  name: "rainforest-lab-demo"

climate:
  mode: "exploration"
  temperature: 1.2
  min_rainfall: 0.15
  seed_budget: 0.20
  max_tree_share: 0.30
  max_consecutive_depth: 2
  novelty_weight: 0.35
  balance_lambda: 0.25
  overfit_penalty: 0.50
  shared_expert_strictness: 0.50

routing:
  germination_threshold: 0.60
  promotion_threshold: 0.75
  seed_slots: 5
  golden_leaf_budget: 0.05
  mutation_budget: 0.05

bias_guard:
  max_user_boost_per_tree: 0.20
  min_budget_for_unselected_trees: 0.08
  require_counterfactual_for_favored_tree: true

storage:
  backend: "sqlite"
  path: "rainforest.db"
```

---

## 16. Implementation Order

Build in this exact order.

### Step 1: Project Skeleton

- Create package structure.
- Add `pyproject.toml`.
- Add basic CLI.
- Add YAML loading utilities.
- Add tests setup.

### Step 2: Core Models

- Implement enums.
- Implement Pydantic models.
- Implement ID utilities.
- Add tests for serialization and validation.

### Step 3: Forest Grounding

- Implement guided interview.
- Implement mapping from answers to config.
- Generate environment, tree profiles, and genesis seeds.
- Add tests with mocked answers.

### Step 4: Weather Router

- Implement moisture scoring.
- Implement drought scoring.
- Implement allocation constraints.
- Generate weather log.
- Add tests for min rainfall, max tree share, and seed budget.

### Step 5: Seed Router and Nursery

- Implement seed scoring.
- Implement active / dormant / rejected routing.
- Implement nursery validation stub.
- Implement basic promotion.

### Step 6: Research Planner

- Convert allocations into tasks.
- Generate task plan JSON and Markdown.
- Add task type support.

### Step 7: Archive Store

- Implement SQLite tables.
- Add insert / fetch / list methods.
- Add Markdown exports.

### Step 8: Result Classification

- Implement rule-based classifier first.
- Later allow LLM-assisted classification.
- Update archive and tree memory.

### Step 9: End-to-End Demo

Create a demo:

```text
examples/quant_mock_cycle/
```

It should show:

```text
init → ground → plan cycle → add mock result → classify → update forest → export report
```

---

## 17. Testing Requirements

### 17.1 Unit Tests

Must test:

- Config loading
- Pydantic model validation
- Forest grounding mapping
- Moisture score calculation
- Weather allocation constraints
- Seed score calculation
- Nursery routing
- Result classification
- Archive CRUD

### 17.2 Critical Weather Tests

Create these tests:

1. No tree exceeds `max_tree_share`.
2. Cold trees receive at least `min_rainfall` when active.
3. Seed budget is preserved.
4. High drought tree receives less allocation.
5. High moisture, low drought tree receives rain.
6. High moisture, high drought tree receives heatwave/drought, not heavy rain.
7. Temperature changes allocation entropy.

### 17.3 Golden Leaf Tests

Create tests for:

1. Failed result with local validity becomes Golden Leaf.
2. Leakage result becomes Sick Leaf.
3. Weak result with no insight becomes Dead Leaf.
4. Golden Leaf can generate seed.

---

## 18. Coding Guidelines

### 18.1 Keep MVP Simple

Prefer clear rule-based implementation over complex ML.

Do not over-engineer.

### 18.2 Make Everything Inspectable

Every routing decision should produce a reason.

Example:

```json
{
  "tree_id": "fund_flow",
  "weather": "rain",
  "allocation": 0.18,
  "reason": "High regime fit and data readiness, capped by max_tree_share."
}
```

### 18.3 No Hidden Decisions

All key parameters must come from config files or explicit defaults.

### 18.4 Domain-neutral Core

Do not hard-code quant-specific logic into core classes.

Put quant-specific examples and experts into configs or optional modules.

### 18.5 Honest Execution

If a real evaluator is not available, use `executor_stub.py` and clearly label results as mock or manual.

Never claim real backtest or real trading performance unless actually computed by a valid evaluator.

---

## 19. Future Extensions

After MVP:

1. LLM provider abstraction
2. Real quant backtest adapter
3. Scientific research adapter
4. Software benchmark adapter
5. Web UI
6. Vector memory
7. Multi-agent tree experts
8. Quality-Diversity archive
9. Regime detector
10. Automatic ablation engine
11. GitHub issue/task integration
12. Paper/report generator

---

## 20. Success Criteria for MVP

The MVP is successful if it can:

1. Initialize a research forest from user-friendly answers.
2. Generate environment config, tree profiles, and seeds.
3. Run a weather allocation cycle.
4. Produce research tasks.
5. Accept experiment results.
6. Classify results into Fruit / Golden Leaf / Leaf types.
7. Update forest memory.
8. Export a readable research report.
9. Demonstrate that weather routing prevents one tree from consuming all attention.
10. Demonstrate that seeds can create new research directions.

---

## 21. First Build Prompt for AI Coding Agent

Use this as the first instruction to the coding agent:

```text
Build the MVP of Rainforest Lab, a seeded, weather-guided research framework for AI agents.

Start by creating a Python package with the directory structure specified in docs/build_spec.md.

Implement the system in this order:
1. Project skeleton and CLI
2. Core Pydantic models and enums
3. YAML config loading
4. Forest Grounding guided interview and mapper
5. Weather Router with moisture, drought, and allocation constraints
6. Seed Router and Nursery stubs
7. Research Task Planner
8. SQLite archive store
9. Result Classifier
10. End-to-end mock demo

Keep the implementation local-first, inspectable, and rule-based.
Do not build trading integrations, web UI, or paid API dependencies.
Every routing decision must include a human-readable reason.
Add pytest tests for all core scoring and routing logic.
```

---

## 22. Naming Conventions

Use these names consistently:

```text
Project name: Rainforest Lab
Core architecture: Research Forest
Initialization phase: Forest Grounding
Scheduling layer: Weather System
New direction layer: Seed System
Validation layer: Nursery
Useful failure memory: Golden Leaf Pool
Storage layer: Archive
Quality control layer: Shared Experts
```

---

## 23. Final Notes

Rainforest Lab should be built as a framework for managing research exploration, not as a black-box alpha generator.

The framework's value comes from structured exploration, transparent routing, useful failure memory, and controlled generation of new research directions.

The first version should be small, testable, and easy for another AI agent or human developer to extend.
