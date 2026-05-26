# Forest Grounding

Use Forest Grounding when a research forest does not exist yet, or when the user's goal has changed enough that the existing forest needs recalibration.

## Interview Questions

Ask natural questions. Do not ask the user to set abstract Rainforest parameters directly.

1. What is the research goal?
2. What market, domain, or problem space is being studied?
3. What data, tools, documents, code, or prior results are available?
4. What cost, frequency, time, policy, or implementation constraints matter?
5. Which mistake is the user most worried about?
6. Which directions should receive an initial boost?
7. Which directions should be avoided or deprioritized?
8. How often should the agent ask for approval before executing work?

## Required Output Fields

Produce or update these fields in `forest-state.yaml`:

```yaml
research_goal: ""
domain: ""
constraints: []
data_soil: {}
initial_trees: []
initial_seeds: []
approval_policy: ""
summary: ""
```

## Mapping Rules

- Broad exploration: increase seed budget, novelty weight, and temperature; lower max tree share.
- Validate candidates: lower temperature and seed budget; increase evidence strictness.
- Repair unstable results: increase overfit penalties, audit tasks, and Sick Leaf sensitivity.
- Fear missing new directions: increase seed slots and novelty weight.
- Fear overfitting: increase leakage checks, promotion threshold, and evidence requirements.
- Fear scattered research: reduce seed slots and task count.
- Fear drilling too deeply: lower max tree share and max consecutive depth.

## Grounding Summary

End grounding with a plain-language summary:

```text
The forest starts in exploration mode.
The system will favor high-potential seeds, but quarantine leakage-prone ideas.
No single tree should dominate the next cycle.
The agent should ask before tool-executed tasks that change files, spend money, or use external accounts.
```
