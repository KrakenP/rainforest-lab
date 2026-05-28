# Multi-Agent Collaboration

Single-pass role pipelines drift: one model imagines, judges, and aligns itself, then ships its
own opinion as evidence. Multi-agent collaboration replaces the pipeline with **a bounded,
adversarial, parallel deliberation inside each cycle** — without giving any LLM the power to
override deterministic gate outcomes.

This file is the v2.0 upgrade to the Rainforest core loop. It sits on top of the same forest
state and weather routing; it does not replace the gate battery or the result classification.

## Role Cast

Every step of a cycle is attributed to a named role. Adding or replacing a participant is a role
registration, not a rewrite.

| Role | Responsibility | Notes |
|---|---|---|
| `coordinator` | Orchestrates the cycle; **sole writer of forest state**. | Stays the arbiter of stop conditions, debate rounds, and merge order. |
| `meteorologist` | Routes attention via weather. | Deterministic; no LLM. |
| `gardener` | Mines hypotheses for one tree. | LLM. v2.0 runs **one gardener per allocated tree**. |
| `inspector` | Pre-nursery judgment: logic, novelty, leakage suspicion. | LLM. |
| `diverger` | Expands candidate mechanisms to alternative formulations. | Handoff to a watching session. |
| `examiner` | Runs the full gate battery on a compiled candidate. | Deterministic. |
| `aligner` | Mechanism-evidence alignment scoring before promotion. | Handoff to a watching session. |
| `skeptic` | Adversarial red-team critique of hypotheses and fruit-candidates. | LLM. **Different model family than the gardener.** |

## The Deliberation Loop (per allocated tree)

```text
gardener mines N hypotheses
  -> skeptic critiques each {weaknesses, overfit_risk, alt_explanations,
                             lookahead_suspicion, verdict, severity}
  -> gardener revises survivors        (<= max_debate_rounds, default 2)
  -> diverger expands survivors        (handoff)
  -> inspector judges -> nursery 7-check -> sprouts
  -> examiner runs the full gate battery
  -> for each fruit-candidate (all hard gates pass):
       skeptic SECOND challenge -> attached to risks, emits skeptic_challenge event,
                                   NEVER alters the gate_record or classification
  -> aligner G7                        (handoff)
  -> classify
```

Per-cycle, the coordinator runs one deliberation per allocated tree and merges the per-tree
results in a deterministic `tree_id`-sorted order. Execution may be concurrent or
independent-sequential; reproducibility is the contract.

## Anti-Self-Favoring: The Different-Model Skeptic

A skeptic that shares the gardener's model family will tend to share its blind spots — and bless
its own mechanisms. The lever:

- The skeptic adapter **structurally refuses** to run when its model family equals the gardener's
  (raise before any API call).
- The system prompt is **adversarial and distinct** from the inspector's judge prompt — it
  assumes the candidate is overfit, spurious, or look-ahead-contaminated until proven otherwise.

Pick the pair before the cycle and freeze it in config (for example: Kimi gardener, DeepSeek
skeptic). Mixing within a family does not count.

## Bounded Debate (Hypothesis Stage)

Per round, for each surviving mechanism:

| Verdict | Severity | Action |
|---|---|---|
| `reject` | `>= cull_severity` | Cull. Drop the mechanism from this cycle. |
| `reject` | `< cull_severity` | Treat as `revise`. |
| `revise` | any | Gardener re-mines a replacement using the skeptic's weaknesses as context. |
| `proceed` | any | Keep the mechanism unchanged; it exits the debate (not re-critiqued). |

The debate ends when every survivor is `proceed` or `max_debate_rounds` is exhausted. After
exhaustion, remaining non-`proceed` survivors are kept (only `reject`-at-or-above-`cull_severity`
is destructive).

`max_debate_rounds == 0` skips the debate entirely; mined mechanisms flow directly into
divergence and inspection. With a single gardener and zero rounds, the loop reproduces the v1
single-pass pipeline.

## Recorded-Only Second Challenge (Fruit Stage)

When all hard gates pass, the skeptic challenges once more before the alignment handoff. The
verdict is:

- **Recorded** as event (`skeptic_challenge`) and attached to the `ResultRecord.risks` field.
- **Not** allowed to alter the `gate_record` or the classification.

Rationale: if an LLM cannot upgrade a stub to a fruit, by symmetry it must not downgrade a
deterministic fruit to a leaf. The second challenge raises rigor as documented adversarial
scrutiny, not as a hidden veto. A skeptic that wants to override a passing gate must instead
propose an explicit, documented gate amendment in the next cycle's grounding.

## Parallel Competing Gardeners

The meteorologist allocates trees; the coordinator dispatches **one gardener per allocated
tree** with distinct temperature/style hints drawn from a `temperature_spread` (for example
`[0.7, 1.0, 1.3]`). This widens the search frontier without changing the validator or the gate
battery. Concurrency is permitted; the contract is a **deterministic merge** of per-tree results
by `tree_id`, so the same seeds always yield the same forest.

## Rigor Invariants (do not break)

1. The validator runs pre- and post-cycle, unchanged.
2. Classification still requires a complete `GateRecord` with `execution_mode == tool_executed`.
   A debated `stub_result` still cannot become a fruit; a skeptic `reject` on a passing
   fruit-candidate does not veto it.
3. The coordinator is the sole writer of forest state. Per-tree deliberation is pure: it reads
   the forest and returns candidate data for the coordinator to merge.
4. Skeptic model family **must** differ from gardener model family. Skeptic or LLM
   unavailability is a hard failure; **no silent fallback**.
5. Backward compatibility: zero debate rounds plus a single gardener reproduces the v1 cycle.

## Event Vocabulary

Every step emits an agent-attributed event to `events.jsonl`. v2.0 adds three action types on
top of the v1 vocabulary; they double as the replay source for an office-scene visualization.

| Action | Emitted by | Carries |
|---|---|---|
| `gardener_parallel_dispatch` | `coordinator` | `{trees, dispatch: {tree_id: temperature}}` |
| `debate_round` | `skeptic` | `{round, in, culled, revised, proceeded}` |
| `skeptic_challenge` | `skeptic` | `{kind: hypothesis | fruit_candidate, verdict, severity, risks}` |

## Suggested Config Block

```yaml
deliberation:
  max_debate_rounds: 2
  skeptic_model: deepseek      # must differ from gardener model family
  gardener_model: kimi
  cull_severity: high          # cull on skeptic verdict=reject AND severity>=this

parallel_gardeners:
  max_concurrent: 4
  temperature_spread: [0.7, 1.0, 1.3]
```

## What v2.0 Deliberately Does Not Do

- It does not evolve research trajectories across cycles (mutation/crossover of full
  hypothesis→AST→code paths). That is a v2.x candidate.
- It does not add a downstream factor-combination layer (ensemble of promoted factors). That is
  a separate strategy-synthesis layer above the framework.
- It does not visualize the deliberation. The event stream is the substrate; a renderer is a
  future, separate concern.
