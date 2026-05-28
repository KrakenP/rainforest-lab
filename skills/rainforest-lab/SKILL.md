---
name: rainforest-lab
description: Use when managing open-ended research, exploring multiple directions, generating or ranking research seeds, preserving useful failures, avoiding fixation on one hypothesis, or using Tree, Seed, Weather, Nursery, Golden Leaf, or research forest concepts.
---

# Rainforest Lab

Use Rainforest to manage open-ended research as a forest of directions. Keep the loop explicit, inspectable, and honest about evidence.

## Core Loop

1. Ground the forest: goal, domain, constraints, data, preferred directions, avoided directions, and approval style.
2. Model active directions as trees and uncertain opportunities as seeds.
3. Research within the allowed execution mode.
4. Capture new seeds continuously during research.
5. Score and rank seeds before sowing.
6. Route attention with weather.
7. Sow only the top seed slots into the nursery.
8. Generate concrete research tasks.
9. Classify every result.
10. Update archive memory before continuing.

## Execution Modes

Every research task must declare one mode:

| Mode | Meaning |
|---|---|
| `plan_only` | Plan only; no evidence gathered. |
| `manual_result` | User supplies the result. |
| `stub_result` | Mock or demonstration result. |
| `tool_executed` | Agent used tools, code, data, or browsing. |

Stub results are not evidence. Tool-executed results must include enough detail to inspect or rerun.

## Multi-Agent Collaboration (v2.0)

Default to a multi-agent deliberation inside each cycle when more than one tree is being mined, or when LLM self-favoring is a known risk. The cast and the deliberation loop are documented in `references/multi-agent-collaboration.md`; the discipline below is binding.

- **Coordinator is the sole writer** of forest state. Per-tree deliberation is pure: read the forest, return candidate data, let the coordinator merge.
- **Parallel competing gardeners** — one per allocated tree, distinct temperature or style. Merge results in a deterministic `tree_id`-sorted order so the cycle is reproducible.
- **Adversarial skeptic with a different model family than the gardener.** The skeptic critiques hypotheses (cull / revise / proceed across bounded debate rounds) and challenges fruit-candidates pre-G7. The fruit-candidate challenge is **recorded only — it cannot veto a passing gate battery**, the same way a debated stub cannot become a fruit.
- **No silent fallback.** Skeptic or LLM unavailable means hard fail. A passing fruit can be debated but cannot be downgraded by an LLM; a stub can be debated but cannot be upgraded.
- **Backward compatible**: `max_debate_rounds = 0` plus a single gardener reproduces the v1 single-pass loop.

New event types (agent-attributed, on `events.jsonl`): `gardener_parallel_dispatch`, `debate_round`, `skeptic_challenge`.

## Load References

- For starting a forest, read `references/forest-grounding.md`.
- For attention allocation, read `references/weather-system.md`.
- For seed capture, scoring, and sowing, read `references/seed-system.md`.
- For low-cost seed checks, read `references/nursery.md`.
- For classifying outcomes, read `references/result-classification.md`.
- For memory updates and reports, read `references/archive-memory.md`.
- For the v2.0 multi-agent deliberation loop (skeptic, parallel gardeners, debate rounds), read `references/multi-agent-collaboration.md`.

## Use Templates

Copy templates from `templates/` when a project lacks structured state. Prefer YAML for state and Markdown for plans and reports.

## Use Scripts

Use `scripts/validate_state.py` before relying on a forest state file. Use `scripts/rainforest_cycle.py` to rank seeds and draft a cycle plan when YAML state is available.
