# Rainforest Lab

[简体中文](README.zh-CN.md)

Rainforest Lab is a seeded, weather-guided research framework for AI agents.

The v0.1 repository is skill-first: its primary artifact is `skills/rainforest-lab/`, a reusable Agent Skill for Claude, Codex, and similar coding agents.

## Install

Copy the skill directory into your agent's skill folder:

```text
skills/rainforest-lab/
```

Claude project install:

```text
.claude/skills/rainforest-lab/
```

Codex install:

```text
.codex/skills/rainforest-lab/
```

## Core Loop

```text
Forest Grounding
-> Tree and Seed Modeling
-> Research Work
-> Continuous Seed Capture
-> Seed Scoring and Ranking
-> Weather Routing
-> Sowing
-> Nursery Validation
-> Research Task Planning
-> Result Classification
-> Archive Update
```

## Multi-Agent Collaboration (v2.0)

The v2.0 upgrade replaces the per-cycle single-pass role pipeline with a **bounded gardener-skeptic deliberation + parallel competing gardeners + an adversarial skeptic from a different model family than the gardener**. The coordinator stays the sole writer of forest state and merges per-tree results in a deterministic, `tree_id`-sorted order, so the cycle is reproducible.

Rigor invariants (test-guarded):

- A debated `stub_result` still cannot become a fruit.
- A skeptic `reject` cannot veto a fruit-candidate that passed every gate — the pre-G7 second challenge is recorded only, never gate-altering.
- The skeptic adapter structurally refuses to run when its model family matches the gardener's (anti-self-favoring).
- No silent fallback: skeptic or LLM unavailable means hard fail.
- `max_debate_rounds = 0` plus a single gardener reproduces the v1 single-pass loop.

See `skills/rainforest-lab/references/multi-agent-collaboration.md` for the full role cast, the deliberation loop, the bounded debate rules, the recorded-only second challenge, and the new agent-attributed event types (`gardener_parallel_dispatch`, `debate_round`, `skeptic_challenge`).

## Execution Honesty

Rainforest allows agents to execute research tasks, but every task must declare one execution mode:

- `plan_only`
- `manual_result`
- `stub_result`
- `tool_executed`

Mock results must never be presented as real evidence.

## License

MIT License. See [LICENSE](LICENSE).
