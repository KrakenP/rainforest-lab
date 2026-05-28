# rainforest-lab Architecture

## Layers

```text
┌──────────────────────────────────────────────────────────────┐
│ Domain plugins (DemoDomain, your market plugin)              │  ← user code
├──────────────────────────────────────────────────────────────┤
│ Kits: dsl (parser/evaluator/random) · gates (G1/G5/G8/G9 +   │
│ net_sharpe + matched_random + profiles)                      │
├──────────────────────────────────────────────────────────────┤
│ Engine: state · validate · classify · weather · seeds ·      │
│ cycle · deliberation · trajectories · roles · events ·       │
│ handoff                                                       │
├──────────────────────────────────────────────────────────────┤
│ LLM: protocols (4) · builders (4) · litellm reference ·      │
│ mocks                                                         │
└──────────────────────────────────────────────────────────────┘
```

## The four rigor invariants

1. **Gate completeness is a type invariant.** `classify` raises if a result would become `fruit`
   without a complete `GateRecord` and `execution_mode == "tool_executed"`.
2. **Single writer.** `cycle.run_cycle` is the only forest-state mutator; `deliberate_tree` and
   trajectory operators are pure read-only.
3. **Different-model skeptic.** `make_llm_skeptic` refuses to run when its model family equals the
   gardener's.
4. **No fruit by lineage.** Trajectory `mutate` / `crossover` produce children with
   `final_classification = None`; sick parents are excluded.

## The deliberation loop (per allocated tree)

Each cycle the coordinator dispatches one gardener per allocated tree. The per-tree deliberation:

```text
gardener.mine(N)                              → N candidate Mechanisms
  → bounded debate (≤ max_debate_rounds):     skeptic.critique each;
                                              cull (reject high-severity), revise (re-mine), proceed.
  → handoff.request("divergence", ...)        → expanded alternative candidates
  → inspector.judge each                      → Judgments → Seeds
  → seeds.rank_and_route + nursery_check      → sprouted tasks
  → domain.evaluate each task                 → GateRecord
  → if fruit-candidate: skeptic.critique      → recorded only (cannot veto a passing gate battery)
  → handoff.request("g7_alignment", ...)      → G7 alignment score merged into gate_record
  → classify                                  → fruit / golden_leaf / normal_leaf / dead_leaf / sick_leaf
```

The coordinator merges per-tree results in `tree_id`-sorted order so the cycle is reproducible.

## Trajectory evolution (v2.1)

Across cycles, `trajectories.mutate(parent)` localizes the failing step (currently the hypothesis
step), freezes the prefix, and lets the gardener rewrite the action. `crossover(parents)` combines
high-reward segments from ≥ 2 healthy parents. Both produce child trajectories whose new hypothesis
becomes a seed for the next cycle — children always start `final_classification=None` and must
flow through the full gate battery (no fruit by lineage). `evolve_seeds_from_archive` is the
end-to-end helper the coordinator can call at cycle start.

## LLM layer — two surfaces

- **Protocols** (`llm.protocols`): four `Protocol` interfaces (`Gardener`, `Inspector`, `Skeptic`,
  `Aligner`). Implement these directly for tight integrations.
- **Builders** (`llm.builders`): `make_llm_X(completion_fn)` wrap any synchronous
  `(system, user) -> str` function into a Protocol implementation. Builders own the adversarial
  system prompts, JSON parse contracts, and (for skeptic) the model-family check.
- **LiteLLM adapter** (`llm.litellm_adapter`): the reference adapter — `litellm_gardener("openai/gpt-5")`
  etc. — covers ~100 providers via the `litellm` extra.

## Handoff

`handoff.py` is the filesystem-based schema'd request/response protocol that v0.1.0 uses for
divergence + G7 alignment. v0.2.0 will replace this with MCP sampling so the host agent's LLM
answers in-band.

## What's deliberately not here (v0.2.0+)

- MCP server (blueprint generator + scaffolder + LLM-config validator + sampling-based handoff).
- Data-discipline kit (PIT calendars, universe-as-of, ST/main-board filters, adjustment regimes).
- CLI (`rainforest ground`, `rainforest mine` with dynamic domain loading).
- Office-scene visualization renderer.
- Downstream factor-combination layer (LightGBM ensemble) — separate research initiative.
