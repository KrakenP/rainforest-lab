# Nursery

The nursery is the low-cost validation layer for seeds. It protects the forest from expanding every attractive idea too early.

## Checks

Evaluate each sown seed:

1. Is the hypothesis clear?
2. Is the required data or evidence available?
3. Is there obvious leakage, future information, or invalid reasoning risk?
4. Is the seed redundant with an active tree?
5. Can the seed be checked cheaply?
6. Is there a plausible local validity condition?
7. Does the seed have a concrete next validation plan?

## Promotion Path

```text
seed -> sprout -> sapling
```

Use:

- `seed`: captured idea, not yet validated.
- `sprout`: clear, non-leaking, and cheap enough for first validation.
- `sapling`: early evidence exists and the next validation path is clear.

## Fail States

- Move unclear but interesting seeds to `hold`.
- Move condition-dependent seeds to `dormant`.
- Move low-value seeds to `reject`.
- Move leakage-prone seeds to `quarantine`.

## Nursery Output

Every nursery decision should include:

```yaml
seed_id: seed_001
decision: sprout
reason: "Clear counterfactual, low validation cost, and no obvious leakage."
next_validation: "Compare behavior across the stated boundary condition."
```
