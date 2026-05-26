# Weather System

Weather routes research attention across trees, seeds, golden leaves, and memory work.

Every weather decision must include a human-readable reason.

## Inputs

Use available evidence to estimate:

| Field | Meaning |
|---|---|
| `moisture` | How much a tree deserves attention now. |
| `drought_need` | Whether a tree is overused, redundant, crowded, or risky. |
| `novelty` | Whether work here may create new information. |
| `golden_leaf_density` | Whether useful failures suggest revival. |
| `data_readiness` | Whether the direction can be validated. |
| `overfit_risk` | Whether excitement is ahead of evidence. |
| `recent_budget_share` | How much recent attention the tree consumed. |
| `redundancy` | Whether the tree repeats another direction. |

## Routing Constraints

- Preserve `seed_budget` for seed and nursery work.
- Cap any tree by `max_tree_share`.
- Preserve at least light attention for active cold trees unless explicitly frozen.
- Do not deepen the same tree beyond `max_consecutive_depth`.
- Penalize high drought need before assigning heavy rain.
- Normalize all allocations so the cycle budget sums to 1.0.

## Weather Types

| Weather | Use When |
|---|---|
| `heavy_rain` | High moisture, low drought, strong next validation path. |
| `rain` | Solid direction deserving normal attention. |
| `drizzle` | Maintain a direction without deepening. |
| `drought` | Reduce attention because the direction is overused or low return. |
| `heatwave` | Excitement, overfit risk, or repeated drilling is too high. |
| `fog` | Evidence is unclear or conflicting. |
| `frost` | Leakage, invalid data, or safety risk freezes work. |
| `wind` | Regime shift or cross-tree migration changes priorities. |
| `thunderstorm` | The forest is stale and needs forced novelty. |

## Weather Log

Every cycle should write:

```yaml
cycle_id: cycle_001
climate_mode: exploration
temperature: 1.2
seed_budget: 0.25
allocations: {}
weather_events:
  - target: tree_or_seed_id
    weather: rain
    allocation: 0.15
    reason: "High novelty and clear validation path, capped by max_tree_share."
```
