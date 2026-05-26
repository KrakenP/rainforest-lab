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

## Execution Honesty

Rainforest allows agents to execute research tasks, but every task must declare one execution mode:

- `plan_only`
- `manual_result`
- `stub_result`
- `tool_executed`

Mock results must never be presented as real evidence.
