# Rainforest Agent Skill Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Rainforest Lab v0.1 agent-skill-first scaffold for Claude and Codex.

**Architecture:** The repository is centered on `skills/rainforest-lab/`. `SKILL.md` stays concise and routes agents to references, templates, and deterministic scripts. YAML and Markdown templates represent forest state, seed bank, weather logs, cycle plans, and reports; Python helper scripts validate state and generate inspectable cycle artifacts.

**Tech Stack:** Markdown Agent Skills, YAML templates, Python 3.11+ standard library, GitHub CLI for private repository publication.

---

## File Structure

- Create `README.md`: explains Rainforest Lab, installation for Claude/Codex, and v0.1 workflow.
- Create `docs/concept.md`: user-facing concept document for Tree, Seed, Weather, Nursery, Golden Leaf, and Archive.
- Create `docs/build_spec.md`: normalized copy of `Rainforest_Lab_Build_Spec.md` for canonical repo docs.
- Create `skills/rainforest-lab/SKILL.md`: concise skill entrypoint and workflow.
- Create `skills/rainforest-lab/agents/openai.yaml`: Codex UI metadata.
- Create `skills/rainforest-lab/references/forest-grounding.md`: grounding questions and mapping outputs.
- Create `skills/rainforest-lab/references/weather-system.md`: weather scoring and routing rules.
- Create `skills/rainforest-lab/references/seed-system.md`: seed capture, scoring, ranking, sowing, and quarantine rules.
- Create `skills/rainforest-lab/references/nursery.md`: seed validation and promotion rules.
- Create `skills/rainforest-lab/references/result-classification.md`: Fruit, Golden Leaf, Leaf, and Sick Leaf classification.
- Create `skills/rainforest-lab/references/archive-memory.md`: state update and report requirements.
- Create `skills/rainforest-lab/templates/forest-state.yaml`: default forest state template.
- Create `skills/rainforest-lab/templates/tree-profile.yaml`: single tree template.
- Create `skills/rainforest-lab/templates/seed-bank.yaml`: seed bank template with scoring fields.
- Create `skills/rainforest-lab/templates/weather-log.yaml`: weather log template.
- Create `skills/rainforest-lab/templates/cycle-plan.md`: cycle planning output template.
- Create `skills/rainforest-lab/templates/cycle-report.md`: cycle report output template.
- Create `skills/rainforest-lab/scripts/rainforest_cycle.py`: deterministic helper to score seeds and draft a cycle plan from YAML state.
- Create `skills/rainforest-lab/scripts/validate_state.py`: deterministic helper to validate required YAML fields.
- Create `examples/quant-research-cycle/`: sample forest state, seed bank, weather log, and cycle report.
- Create `examples/generic-research-cycle/`: generic non-quant example.

---

### Task 1: Repository Documentation Shell

**Files:**
- Create: `README.md`
- Create: `docs/concept.md`
- Create: `docs/build_spec.md`

- [ ] **Step 1: Create `README.md`**

Write:

```markdown
# Rainforest Lab

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
```

- [ ] **Step 2: Create `docs/concept.md`**

Write a concise concept guide with these sections:

```markdown
# Rainforest Lab Concept

## Forest

The forest is the complete research state: goals, constraints, active directions, seeds, weather history, and archive memory.

## Tree

A tree is an established research direction receiving recurring attention.

## Seed

A seed is a potential new direction. Seeds are captured continuously during research, scored, ranked, and only then sown into the nursery.

## Weather

Weather routes attention. It prevents one promising direction from consuming the whole research process.

## Nursery

The nursery validates seeds cheaply before they become larger commitments.

## Golden Leaf

A Golden Leaf is a useful failure: a failed result that reveals a boundary condition, sub-regime, counterexample, or future seed.

## Archive

The archive stores forest state, cycle reports, weather decisions, seed decisions, and result classifications so future agents can resume research.
```

- [ ] **Step 3: Create `docs/build_spec.md`**

Copy the content from `Rainforest_Lab_Build_Spec.md` into `docs/build_spec.md` without changing the original file.

- [ ] **Step 4: Commit**

Run:

```powershell
git add README.md docs/concept.md docs/build_spec.md
git commit -m "docs: add Rainforest repository documentation"
```

Expected: commit succeeds with the configured GitHub noreply author.

---

### Task 2: Skill Entrypoint and UI Metadata

**Files:**
- Create: `skills/rainforest-lab/SKILL.md`
- Create: `skills/rainforest-lab/agents/openai.yaml`

- [ ] **Step 1: Create directories**

Run:

```powershell
New-Item -ItemType Directory -Force -Path skills/rainforest-lab/agents | Out-Null
```

- [ ] **Step 2: Create `skills/rainforest-lab/SKILL.md`**

Write:

```markdown
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
```

- [ ] **Step 3: Create `skills/rainforest-lab/agents/openai.yaml`**

Write:

```yaml
display_name: Rainforest Lab
short_description: Manage open-ended research with trees, seeds, weather routing, and useful failure memory.
default_prompt: Use Rainforest Lab to ground my research goal, organize trees and seeds, route attention with weather, and produce the next cycle plan.
```

- [ ] **Step 4: Validate frontmatter manually**

Run:

```powershell
Select-String -Path skills/rainforest-lab/SKILL.md -Pattern '^---$|^name:|^description:'
```

Expected: two `---` delimiters, one `name`, and one `description`.

- [ ] **Step 5: Commit**

Run:

```powershell
git add skills/rainforest-lab/SKILL.md skills/rainforest-lab/agents/openai.yaml
git commit -m "feat: add Rainforest agent skill entrypoint"
```

---

### Task 3: Reference Guides

**Files:**
- Create all files under `skills/rainforest-lab/references/`

- [ ] **Step 1: Create directory**

Run:

```powershell
New-Item -ItemType Directory -Force -Path skills/rainforest-lab/references | Out-Null
```

- [ ] **Step 2: Create `forest-grounding.md`**

Include questions for goal, domain, data, constraints, feared mistakes, emphasized directions, avoided directions, and approval style. Require output fields: `research_goal`, `domain`, `constraints`, `data_soil`, `initial_trees`, `initial_seeds`, `approval_policy`, and `summary`.

- [ ] **Step 3: Create `weather-system.md`**

Define moisture and drought inputs, weather outputs, and the rule that every weather decision needs a reason. Include active constraints: preserve `seed_budget`, cap tree share with `max_tree_share`, and avoid repeated deepening beyond `max_consecutive_depth`.

- [ ] **Step 4: Create `seed-system.md`**

Include the high-potential seed score:

```text
0.25 * novelty
+0.20 * logic_strength
+0.15 * option_value
+0.15 * cross_tree_potential
+0.10 * regime_relevance
+0.10 * evidence_hint
+0.05 * data_availability
-0.15 * validation_cost
-0.20 * leakage_risk
-0.10 * redundancy
```

Require routing to `sow_now`, `hold`, `dormant`, `reject`, or `quarantine`.

- [ ] **Step 5: Create `nursery.md`**

Define checks for hypothesis clarity, data availability, leakage risk, redundancy, validation cost, local validity condition, and next validation plan. Define promotion path `seed -> sprout -> sapling`.

- [ ] **Step 6: Create `result-classification.md`**

Define Fruit, Golden Leaf, Normal Leaf, Dead Leaf, and Sick Leaf. Require Golden Leaf seed generation and Sick Leaf warning memory.

- [ ] **Step 7: Create `archive-memory.md`**

Define required updates after each cycle: forest state, seed bank, weather log, cycle report, golden leaf pool, warnings, and next questions.

- [ ] **Step 8: Commit**

Run:

```powershell
git add skills/rainforest-lab/references
git commit -m "docs: add Rainforest reference guides"
```

---

### Task 4: Templates

**Files:**
- Create all files under `skills/rainforest-lab/templates/`

- [ ] **Step 1: Create directory**

Run:

```powershell
New-Item -ItemType Directory -Force -Path skills/rainforest-lab/templates | Out-Null
```

- [ ] **Step 2: Create YAML templates**

Create:

```text
forest-state.yaml
tree-profile.yaml
seed-bank.yaml
weather-log.yaml
```

Each YAML file must include sample values, required fields, and comments explaining how agents should update it.

- [ ] **Step 3: Create Markdown templates**

Create:

```text
cycle-plan.md
cycle-report.md
```

`cycle-plan.md` must include sections for weather summary, seed sowing queue, research tasks, execution modes, and evidence requirements.

`cycle-report.md` must include sections for completed tasks, result classifications, new seeds, archive updates, and next cycle.

- [ ] **Step 4: Commit**

Run:

```powershell
git add skills/rainforest-lab/templates
git commit -m "feat: add Rainforest state and report templates"
```

---

### Task 5: Deterministic Helper Scripts

**Files:**
- Create: `skills/rainforest-lab/scripts/rainforest_cycle.py`
- Create: `skills/rainforest-lab/scripts/validate_state.py`

- [ ] **Step 1: Create directory**

Run:

```powershell
New-Item -ItemType Directory -Force -Path skills/rainforest-lab/scripts | Out-Null
```

- [ ] **Step 2: Create `rainforest_cycle.py`**

Implement a standard-library Python script that reads a YAML-like seed bank using a simple JSON fallback only if PyYAML is unavailable, computes the default seed score, sorts seeds, and prints a Markdown sowing queue. If YAML parsing is unavailable and input is not JSON, print a clear error telling the agent to install PyYAML or convert the file to JSON.

- [ ] **Step 3: Create `validate_state.py`**

Implement a standard-library Python script that checks for required top-level keys in forest state and seed bank files. It should print `OK` on success and list missing keys on failure.

- [ ] **Step 4: Smoke test scripts**

Run:

```powershell
& 'C:\Users\LHPiv\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' skills/rainforest-lab/scripts/validate_state.py --help
& 'C:\Users\LHPiv\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' skills/rainforest-lab/scripts/rainforest_cycle.py --help
```

Expected: both commands print usage text and exit successfully.

- [ ] **Step 5: Commit**

Run:

```powershell
git add skills/rainforest-lab/scripts
git commit -m "feat: add Rainforest helper scripts"
```

---

### Task 6: Examples

**Files:**
- Create files under `examples/quant-research-cycle/`
- Create files under `examples/generic-research-cycle/`

- [ ] **Step 1: Create directories**

Run:

```powershell
New-Item -ItemType Directory -Force -Path examples/quant-research-cycle | Out-Null
New-Item -ItemType Directory -Force -Path examples/generic-research-cycle | Out-Null
```

- [ ] **Step 2: Create quant example**

Create a mock A-share quant research cycle with:

- `forest-state.yaml`
- `seed-bank.yaml`
- `weather-log.yaml`
- `cycle-report.md`

Use execution modes honestly. Any sample result must be marked `stub_result`.

- [ ] **Step 3: Create generic example**

Create a non-quant research cycle about evaluating documentation improvement strategies with the same four files.

- [ ] **Step 4: Validate examples**

Run:

```powershell
& 'C:\Users\LHPiv\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' skills/rainforest-lab/scripts/validate_state.py examples/quant-research-cycle/forest-state.yaml examples/quant-research-cycle/seed-bank.yaml
& 'C:\Users\LHPiv\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' skills/rainforest-lab/scripts/validate_state.py examples/generic-research-cycle/forest-state.yaml examples/generic-research-cycle/seed-bank.yaml
```

Expected: both commands print `OK`.

- [ ] **Step 5: Commit**

Run:

```powershell
git add examples
git commit -m "test: add Rainforest example research cycles"
```

---

### Task 7: Final Verification and Publication

**Files:**
- Modify as needed based on verification.

- [ ] **Step 1: Check repository status**

Run:

```powershell
git status --short --branch
```

Expected: clean working tree before publication.

- [ ] **Step 2: Check GitHub CLI auth**

Run:

```powershell
& 'E:\rainforest\.tools\gh\bin\gh.exe' auth status
```

Expected: logged in as `KrakenP`.

- [ ] **Step 3: Create private repository if missing**

Run:

```powershell
& 'E:\rainforest\.tools\gh\bin\gh.exe' repo create rainforest-lab --private --source . --remote origin --description "Agent skill for seeded, weather-guided research orchestration" --push
```

Expected: private repository `KrakenP/rainforest-lab` exists and local commits are pushed.

- [ ] **Step 4: Verify remote**

Run:

```powershell
git remote -v
& 'E:\rainforest\.tools\gh\bin\gh.exe' repo view KrakenP/rainforest-lab --json name,visibility,url
```

Expected: visibility is `PRIVATE`.

---

## Self-Review

Spec coverage:

- Skill-first scaffold: Tasks 1-2.
- References for rules: Task 3.
- Templates for state and reports: Task 4.
- Deterministic scripts: Task 5.
- Quant and generic examples: Task 6.
- Private GitHub publication: Task 7.

Placeholder scan:

- Forbidden placeholder terms are absent.

Type and naming consistency:

- Skill path is consistently `skills/rainforest-lab/`.
- GitHub repo name is consistently `rainforest-lab`.
- Execution modes match the approved design.
