# Changelog

All notable changes to `rainforest-lab` (the Python package) are documented here. The format
follows [Keep a Changelog](https://keepachangelog.com/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.1.0] — Unreleased

### Added

- **Engine**: `state` · `validate` · `classify` · `weather` · `seeds` · `cycle` · `deliberation`
  · `trajectories` · `roles` · `events` · `handoff` (clean-room port from the rainforest engine;
  project couplings removed).
- **Multi-agent (v2.0)**: bounded gardener-skeptic deliberation, parallel competing gardeners,
  recorded-only second challenge before G7.
- **Trajectory evolution (v2.1)**: `mutate` / `crossover` / `evolve_seeds_from_archive`
  primitives; "no fruit by lineage" invariant.
- **DSL kit**: `OpRegistry`, AST parser, evaluator, deterministic random-formula generator.
- **Gates kit**: parameterized `g1_sanity` / `g5_turnover` / `g8_decay` / `g9_liquidity` /
  `net_sharpe`, `matched_random_threshold` helper, YAML gates-profile loader.
- **LLM layer**: four `Protocol`s (Gardener / Inspector / Skeptic / Aligner), four
  `make_llm_X(completion_fn)` builders that own the adversarial prompts + JSON parsing, LiteLLM
  reference adapter (~100 providers behind one interface), mocks for tests.
- **Reference domain**: `DemoDomain` using the kits — ~190 lines, doubles as the template for
  writing your own.
- **Domain helper**: `ResearchDomain.cache_dir()` default method so each plugin gets a sane
  per-domain cache directory (`./runs/<name>/cache/`) without re-implementing it.
- **Examples**: `quick_start.py`, `bring_your_own_llm.py`, `write_your_own_domain.py`.

### Out of scope (planned for v0.2.0)

- MCP server with blueprint generator + scaffolder + LLM-config validator.
- Sampling-based handoff (replacing the filesystem-based handoff).
- Data-discipline kit (PIT helpers, calendar/universe-as-of helpers).
- CLI with dynamic domain loading.

[0.1.0]: https://github.com/KrakenP/rainforest-lab/releases/tag/v0.1.0
