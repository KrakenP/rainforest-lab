# Rainforest Agent Skill Scaffold Design

## Status

Approved direction: build Rainforest Lab v0.1 as an agent-skill-first scaffold.

Rainforest Lab is a reusable research thinking system for AI coding agents. It is not primarily a traditional Python application in v0.1. The first version should behave like a high-quality agent skill: concise enough to trigger and use, structured enough to preserve research state, and practical enough to guide Claude, Codex, or similar agents through open-ended research cycles.

## Product Intent

Rainforest helps an agent manage open-ended research as a living forest:

- Trees are established research directions.
- Branches are hypotheses under a tree.
- Seeds are potential new directions.
- The nursery validates seeds cheaply before promotion.
- Weather routes attention and research budget.
- Fruits are useful positive results.
- Golden leaves are useful failures.
- Sick leaves are invalid or dangerous findings that must not be reused.
- Archive memory keeps cycle history reusable.

The first version should make an agent better at deciding where to look next, when to stop over-digging, how to preserve valuable failures, and how to generate new high-potential directions during research.

## Trigger Boundary

Rainforest should trigger broadly and execute narrowly.

Use it when the user asks for:

- Open-ended research.
- Multi-direction exploration.
- Hypothesis management.
- Avoiding fixation on one promising direction.
- Preserving failed experiments and boundary cases.
- Generating new research directions while working.
- Using Tree, Seed, Weather, Nursery, or Golden Leaf language.

Rainforest should not default to paid APIs, live trading, brokerage integrations, web apps, or claims of profitable strategies. It can execute research tasks when tools and data are available, but every task must clearly label how the result was produced.

## Core Workflow

The skill should guide the agent through this loop:

1. Forest Grounding
   Convert the user's research intent into a starting forest state: goal, domain, constraints, data availability, preferred directions, avoided directions, approval style, and bias concerns.

2. Tree and Seed Modeling
   Put established directions into trees. Put uncertain or speculative directions into the seed bank.

3. Research Work
   Let the agent perform planning, reading, analysis, coding, data inspection, or user-guided research depending on available tools and the requested execution mode.

4. Continuous Seed Capture
   During research, capture new seeds from insights, failures, cross-tree associations, counterfactuals, regime shifts, new data sources, and user-supplied external knowledge.

5. Seed Scoring and Ranking
   Score seeds before sowing them. The default policy favors high-potential new directions, while still penalizing leakage risk, redundancy, and excessive validation cost.

6. Weather Routing
   Allocate attention across active trees, seed nursery, golden leaf revival, counterfactual checks, and memory summarization. Weather should prevent a single tree from consuming all attention.

7. Sowing
   Sow only a limited number of top-ranked seeds per cycle. Default `seed_slots` should be 3.

8. Nursery Validation
   Validate sown seeds cheaply. A seed can become a sprout or sapling only after passing basic clarity, data, leakage, redundancy, and validation-plan checks.

9. Research Task Planning
   Produce concrete tasks with hypothesis, budget, validation plan, expected output, execution mode, and evidence requirements.

10. Result Classification
    Classify every result as Fruit, Golden Leaf, Normal Leaf, Dead Leaf, or Sick Leaf.

11. Archive Update
    Update forest state, seed bank, weather log, cycle report, golden leaf pool, and warnings before the next cycle.

## Seed System

Seeds are first-class memory objects. An agent may create seeds at any time while researching, but seeds should not be expanded immediately. They enter the seed bank first.

Seed sources include:

- Fresh ideas from current research.
- Failed-result boundary conditions.
- Golden leaf revival opportunities.
- Cross-tree combinations.
- Regime changes.
- Counterfactual checks.
- New data sources.
- External knowledge supplied by the user.
- Controlled random mutations.

Default seed score:

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

Seed routing states:

- `sow_now`: high-priority seed for the next nursery pass.
- `hold`: valuable but not selected for the next cycle.
- `dormant`: useful only under future conditions.
- `reject`: low value or unclear.
- `quarantine`: suspected leakage, spurious relationship, or hazardous reasoning.

High leakage risk should route to `quarantine` even if the seed otherwise looks attractive. High potential should matter, but Rainforest must not turn speculative enthusiasm into unmarked evidence.

## Weather System

Weather is the attention scheduler.

Inputs should include:

- `moisture`: how much a tree deserves attention now.
- `drought_need`: whether a tree is overused, redundant, crowded, or risky.
- `novelty`: whether the direction may add new information.
- `golden_leaf_density`: whether useful failures suggest revival.
- `data_readiness`: whether the direction can be validated.
- `overfit_risk`: whether the direction is too exciting for the evidence.
- `recent_budget_share`: how much attention the direction recently consumed.
- `redundancy`: whether it repeats another direction.

Weather outputs:

- `rain`: normal investment.
- `heavy_rain`: strong investment.
- `drizzle`: small maintenance allocation.
- `drought`: pause or reduce attention.
- `heatwave`: over-excitement or overfit warning.
- `fog`: unclear evidence.
- `frost`: risk freeze.
- `wind`: regime shift or cross-tree migration.
- `thunderstorm`: forced novelty injection when the forest is stale.

Every weather decision must include a human-readable reason.

## Execution Modes

Rainforest may allow the agent to execute research tasks. Each task and result must label execution mode:

- `plan_only`: the agent only plans the research.
- `manual_result`: the user supplies the result.
- `stub_result`: the result is mock or demonstration-only.
- `tool_executed`: the agent actually used tools, code, data, or browsing to validate something.

Stub results must never be described as real evidence. Tool-executed results must include enough evidence references for a later agent to inspect or rerun the work.

## Result Classification

Classify every result.

- Fruit: initially useful result with a next validation path. Fruit means research value, not tradability or proof.
- Golden Leaf: failed overall, but reveals a boundary condition, sub-regime, counterexample, low-correlation weak signal, or new seed.
- Normal Leaf: ordinary failed result with limited insight.
- Dead Leaf: weak logic, weak evidence, no revival value.
- Sick Leaf: leakage, future function, overfit artifact, invalid data handling, or spurious relationship.

Golden Leaves should generate seeds when possible. Sick Leaves should enter warning memory and must not be reused as positive evidence.

## Repository Shape

The v0.1 repository should be skill-first:

```text
rainforest/
  README.md
  docs/
    concept.md
    build_spec.md
  skills/
    rainforest-lab/
      SKILL.md
      agents/
        openai.yaml
      references/
        forest-grounding.md
        weather-system.md
        seed-system.md
        nursery.md
        result-classification.md
        archive-memory.md
      templates/
        forest-state.yaml
        tree-profile.yaml
        seed-bank.yaml
        weather-log.yaml
        cycle-plan.md
        cycle-report.md
      scripts/
        rainforest_cycle.py
        validate_state.py
  examples/
    quant-research-cycle/
    generic-research-cycle/
```

The Python scripts are support tools, not the primary product. They should validate state files, rank seeds, draft cycle plans, and produce inspectable outputs.

## Claude and Codex Compatibility

The canonical skill should live at:

```text
skills/rainforest-lab/
```

Users can copy it into:

```text
.claude/skills/rainforest-lab/
.codex/skills/rainforest-lab/
```

The skill should follow the common Agent Skills pattern:

- `SKILL.md` contains concise triggering and workflow instructions.
- `references/` contains detailed rules loaded only when needed.
- `templates/` contains state/report templates.
- `scripts/` contains deterministic helpers.
- `agents/openai.yaml` exposes display metadata for Codex-style UIs.

## MVP Success Criteria

Rainforest v0.1 succeeds when an agent can:

1. Ground a user's research intent into a forest state.
2. Maintain trees and a seed bank.
3. Generate seeds during research.
4. Score and rank seeds with a high-potential bias.
5. Sow a limited number of seeds per cycle.
6. Use weather routing to avoid over-investing in one tree.
7. Produce concrete research task plans.
8. Execute tasks when allowed and label execution mode honestly.
9. Classify results into Fruit, Golden Leaf, Normal Leaf, Dead Leaf, or Sick Leaf.
10. Update archive memory and export a readable cycle report.
11. Be reusable by Claude and Codex as a skill.

## Out of Scope for v0.1

- Real brokerage integration.
- Live trading.
- Profitability claims.
- Full web app.
- Vector database dependency.
- Complex workflow engine.
- Default paid API usage.
- Production-grade backtesting.
- Multi-agent execution framework dependency.

## Design Checks

- No placeholders remain.
- The design is skill-first, not app-first.
- Seed generation during research is part of the core loop.
- Seed ranking favors high-potential new directions.
- Agent execution is allowed but must be labeled by execution mode.
- Weather, seed, and result decisions require inspectable reasons.
