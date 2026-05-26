# Result Classification

Classify every research result before updating memory.

## Labels

| Label | Meaning |
|---|---|
| `fruit` | Initially useful result with a next validation path. |
| `golden_leaf` | Failed overall but revealed a boundary, sub-regime, counterexample, low-correlation weak signal, or new seed. |
| `normal_leaf` | Ordinary failed result with limited insight. |
| `dead_leaf` | Weak logic, weak evidence, and no revival value. |
| `sick_leaf` | Leakage, future function, overfit artifact, invalid data handling, non-reusable or spurious relationship. |

Fruit means research value, not proof, tradability, or profitability.

## Required Fields

```yaml
result_id: result_001
task_id: task_001
execution_mode: tool_executed
classification: golden_leaf
summary: ""
evidence: []
risks: []
classification_reason: ""
generated_seeds: []
revival_condition: ""
blocked_from_reuse: false
```

## Rules

- Mark leakage, future information, and invalid data handling as `sick_leaf`.
- A failed result with a useful boundary condition is `golden_leaf`, not `dead_leaf`.
- Generate seeds from Golden Leaves when they suggest a new direction.
- Store Sick Leaves as warnings and block them from positive reuse.
- Never upgrade `stub_result` evidence into a Fruit without real validation.
