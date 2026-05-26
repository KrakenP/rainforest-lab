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

## Load References

- For starting a forest, read `references/forest-grounding.md`.
- For attention allocation, read `references/weather-system.md`.
- For seed capture, scoring, and sowing, read `references/seed-system.md`.
- For low-cost seed checks, read `references/nursery.md`.
- For classifying outcomes, read `references/result-classification.md`.
- For memory updates and reports, read `references/archive-memory.md`.

## Use Templates

Copy templates from `templates/` when a project lacks structured state. Prefer YAML for state and Markdown for plans and reports.

## Use Scripts

Use `scripts/validate_state.py` before relying on a forest state file. Use `scripts/rainforest_cycle.py` to rank seeds and draft a cycle plan when YAML state is available.
