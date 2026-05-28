# 🌳 Rainforest Lab

> **Honest multi-agent research, structurally enforced.**
> Plant a research direction → grow it into a forest of hypotheses → only what survives every gate becomes evidence.

[简体中文](README.zh-CN.md) · License: MIT · Status: `skill` ✅ · `python package` 🚧 · `mcp server` 📅

Rainforest Lab is a **market-agnostic research framework** for AI agents. It treats open-ended investigation as a *forest of directions* — with seeds, weather, golden leaves, an adversarial skeptic, and gates that an LLM cannot bless its way through.

The whole thing is built around one stubborn idea: **"no alpha here" is a legitimate scientific outcome**, and a framework that lets an LLM declare victory unchecked is the bug, not the feature.

---

## 🌱 Where this is heading

```text
You:    "I want to research whether A-share bank earnings differentials predict
         next-month excess returns."

Claude: [confirms direction · asks 3 clarifying questions]
        [calls rainforest-lab MCP] → blueprint proposed
        [user reviews + tweaks: 'add P/B ratio to fields']
        [writes 5 files to your project dir, with your approval]
        [walks you through LLM config: gardener? skeptic? — different model families]
        "Ready. Want me to start mining? (target 5 fruits, max 4h)"

You:    "Go."

[Cycle 1 → 3 candidates evaluated → 0 fruit, 2 golden_leaf, 1 dead.   ← honest report]
[Cycle 2 → ...]
```

No code written by hand. No magic-alpha claims. Just a self-running, falsifiable investigation with the user in the loop on **the direction**, not the plumbing.

---

## 📦 The three pillars

| Pillar | What it is | Status |
|---|---|---|
| 📚 **Skill** — `skills/rainforest-lab/` | Methodology spec + templates: forest grounding, weather, seeds, nursery, classification, archive memory, multi-agent collaboration (v2.0) | ✅ shipped |
| 🛠️ **Python Package** — `python/rainforest_lab/` | Market-agnostic engine: state · validate · cycle · deliberation · trajectories · DSL kit · gates kit · LLM Protocols + LiteLLM reference adapter | 🚧 v0.1.0 in progress |
| 🔌 **MCP Server** — `mcp/` | The product surface: blueprint generator + scaffolder + LLM config validator + engine driver via MCP sampling | 📅 v0.2.0 (the product release) |

The skill teaches the methodology. The package implements it. The MCP server packages it into a product an end user can talk to.

---

## 🌧️ 🌳 🍎 The metaphor (and why it isn't just cute)

| Symbol | Concept | What it does |
|---|---|---|
| 🌳 **Tree** | A research direction under active investment | Has branches (hypothesis lineage), a budget share, and weather priors |
| 🌱 **Seed** | A potential new direction | Scored on 10 dimensions before being sown |
| ☀️🌧️🌪️ **Weather** | Per-cycle attention router | 13 weathers — heavy_rain · rain · drizzle · drought · heatwave · frost · thunderstorm · fog · wind · spring · monsoon · flood · wildfire |
| 🌿 **Nursery** | Low-cost pre-gate validation | 7 bounded checks before paying for evaluation |
| 🍎 **Fruit** | A factor that passed every hard gate + alignment | PROMOTED (G7 ≥ 2) or ENSEMBLE (G7 ≥ 1) |
| 🍃 **Golden Leaf** | A useful failure | Boundary-informative; emits seeds for future revival |
| 🟥 **Sick Leaf** | A poisoned result (lookahead / leakage) | Blocked from reuse; warning persists across cycles |

Symbols make the loop **inspectable** — every step has a reason and a metaphor that maps cleanly onto code.

---

## 🤖 Multi-agent deliberation (v2.0)

Single-pass role pipelines drift: one model imagines, judges, and aligns itself, then ships its own opinion as evidence. v2.0 replaces the pipeline with a **bounded gardener ↔ skeptic deliberation + parallel competing gardeners + an adversarial skeptic from a different model family than the gardener**.

- 🗣️ **Skeptic (red-team critic)** — uses a *different model family* than the gardener (e.g. gardener Kimi ↔ skeptic DeepSeek, or gardener OpenAI ↔ skeptic Anthropic). The skeptic adapter **structurally refuses** to run when families match.
- 🔁 **Bounded debate** — `gardener mines → skeptic critiques (cull / revise / proceed) → gardener revises survivors` up to `max_debate_rounds`. Then the rest of the pipeline (divergence → inspector → nursery → examiner) takes over.
- 🍎 **The second challenge is recorded, never vetoing** — a pre-G7 skeptic challenge on a fruit-candidate *cannot* override the deterministic gate battery. Symmetric to "a debated stub still cannot become a fruit": **the LLM may neither create nor kill what the deterministic gates judged**.
- 🌳🌳🌳 **Parallel gardeners** — one per allocated tree, distinct temperature/style, deterministic `tree_id`-sorted merge for reproducibility.

📖 Full spec: [`skills/rainforest-lab/references/multi-agent-collaboration.md`](skills/rainforest-lab/references/multi-agent-collaboration.md).

---

## 🧬 Trajectory evolution (v2.1)

Instead of evolving factor strings within a cycle, **evolve whole reasoning paths across cycles** — inspired by trajectory-level innovation in recent literature, hardened with the rainforest's rigor model.

- 🧬 **Mutate** — localize the failing step of a parent trajectory, freeze the prefix, rewrite via the gardener.
- ⛓️ **Crossover** — recombine high-reward segments from ≥ 2 healthy parents.
- 🛡️ **No fruit by lineage** — children always start unclassified; they must flow through the full gate battery. The same way an LLM can't upgrade a stub to a fruit, it can't inherit one.
- ☢️ **Sick parents are poisoned** — never selected for mutation or crossover. Lookahead does not propagate.

Primitives shipped; coordinator integration is opt-in.

---

## 🔒 The discipline (the actual differentiator)

Most "LLM does X" pipelines ship a beautiful workflow that reports a nice number, no significance testing, and no honest failures. Rainforest is built from a real post-mortem (**76 "wins" reduced to 1 by stricter gates**), so the framework is structurally allergic to:

- 🚦 **Gate completeness is a type invariant** — a result cannot classify as `fruit` without a complete `GateRecord` and `execution_mode == tool_executed`. The "76 pseudo-fruits" class of bug is structurally impossible, not merely discouraged.
- 📏 **Matched-random P99 significance bar** — G3 forces OOS Sharpe > the P99 of 1000 random factors under the same regime mask. Frozen with provenance (`{date, N, universe, percentile}`).
- 🤐 **No silent fallback** — LLM unavailable means hard fail. A synthetic fallback dressed as a real result is treated as a bug, not a feature.
- ☝️ **Single source of truth** — only canonical YAML state is read/written by the engine; derived JSON is one-directional and never re-ingested.
- 🎯 **Sonnet-drivable North Star** — guardrails strong enough that a weaker model can drive the loop without drifting. Even Opus drifted in the predecessor effort.
- 📉 **0/N is a legitimate result** — reporting "no alpha here" is a feature, not a failure. Publishable.

---

## ⚡ Quick start

**Today (v0.1 skill is shipped):**

```bash
# Claude
cp -r skills/rainforest-lab/ ~/.claude/skills/

# Codex
cp -r skills/rainforest-lab/ ~/.codex/skills/
```

Then ask your agent:

> *"Use rainforest-lab to plan my research on [your topic]."*

The agent reads the methodology, walks you through forest grounding, and produces a cycle plan you can execute yourself.

**Coming (v0.1.0 Python package + v0.2.0 MCP server):**

```bash
# Python developer path — drive the engine programmatically
pip install rainforest-lab

# End-user path — talk to your host agent (Claude Desktop / Cursor / ...)
claude mcp add rainforest-lab
```

⭐ Star this repo to follow the v0.1.0 / v0.2.0 releases.

---

## 🗺️ Roadmap

| Version | Scope | Status |
|---|---|---|
| **v0.1 — skill** | Methodology spec + templates + v2.0 multi-agent collaboration content | ✅ shipped |
| **v0.1.0 — engine** | `pip install rainforest-lab`: engine + LLM Protocols + LiteLLM reference adapter + DSL kit + gates kit + trajectory primitives | 🚧 in progress |
| **v0.2.0 — product** | MCP server: blueprint generator + scaffolder + LLM config validator + sampling-based handoff (replaces filesystem handoff) | 📅 next |
| **v0.3+** | Office-scene visualization (multi-agent collaboration as a watchable scene) · more blueprint templates · downstream factor combination (ensemble layer) | 🔮 later |

---

## 🌱 Contributing

Domain plugins, LLM adapters, and blueprint templates are first-class citizens.

Once the package lands, writing a domain plugin should be:

1. Pick a blueprint template (or talk to the MCP server: *"I want to research X on market Y"*).
2. Register your fields and operators with `rainforest_lab.dsl` — get parsing, evaluation, random-formula generation, and complexity inference for free.
3. Supply a gates threshold profile in YAML — get the full gate battery parameterized to your market.
4. Implement `ResearchDomain` — typically ~150 lines.
5. Ship.

The rigor invariants are non-negotiable; everything else is open. PRs and issues welcome.

---

## 📜 License

MIT. See [LICENSE](LICENSE).

---

> Built from a real `76 pseudo-fruits → 1` post-mortem. Every gate, every debate, and every invariant earns its keep — because someone learned the hard way that an LLM declaring victory isn't the same as the gates passing. 🍃
