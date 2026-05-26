# Seed System

Seeds are potential new research directions. Capture them continuously, but score and rank them before sowing.

## Capture Sources

- Fresh ideas from current research.
- Failed-result boundary conditions.
- Golden Leaf revival opportunities.
- Cross-tree combinations.
- Regime changes.
- Counterfactual checks.
- New data sources.
- External knowledge supplied by the user.
- Controlled random mutations.

## Required Seed Fields

```yaml
seed_id: seed_001
idea: ""
source_type: genesis
related_trees: []
scores:
  novelty: 0.5
  logic_strength: 0.5
  option_value: 0.5
  cross_tree_potential: 0.5
  regime_relevance: 0.5
  evidence_hint: 0.5
  data_availability: 0.5
  validation_cost: 0.5
  leakage_risk: 0.5
  redundancy: 0.5
status: hold
validation_plan: ""
reason: ""
```

## Default Score

Rainforest v0.1 favors high-potential new directions:

```text
0.25 * novelty
+0.20 * logic_strength
+0.15 * option_value
+0.15 * cross_tree_potential
+0.10 * regime_relevance
+0.10 * evidence_hint
+0.05 * data_availability
-0.15 * validation_cost
-0.20 * leakage_risk
-0.10 * redundancy
```

## Routing States

| State | Meaning |
|---|---|
| `sow_now` | High-priority seed for the next nursery pass. |
| `hold` | Valuable but not selected for the next cycle. |
| `dormant` | Useful only under future regime, data, or timing conditions. |
| `reject` | Low value, unclear, or too expensive for current goals. |
| `quarantine` | Suspected leakage, spurious relationship, or hazardous reasoning. |

## Sowing Rules

- Default `seed_slots` is 3.
- Sort by seed score after applying quarantine checks.
- High leakage risk routes to `quarantine` even when the seed score is high.
- Each sown seed needs a first validation plan.
- Counterfactual seeds are required when the agent or user is over-favoring one tree.
