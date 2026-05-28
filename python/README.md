# rainforest-lab (Python package)

`pip install rainforest-lab` — the engine of the rainforest research framework.

This package implements the rainforest engine (v1 + v2.0 multi-agent deliberation + v2.1 trajectory
primitives), four LLM Protocols, a LiteLLM reference adapter, and two reusable kits (`dsl`, `gates`)
so each new domain plugin stays ~150 lines.

See the [top-level README](../README.md) for the project vision; this README is package-level.

## Install

```bash
pip install rainforest-lab
# Optional: LiteLLM reference adapter (~100 providers behind one interface)
pip install "rainforest-lab[litellm]"
```

## 30-second tour

```python
from rainforest_lab import (
    DemoDomain, Forest, run_cycle,
    MockGardener, MockInspector, MockSkeptic,
    DeliberationConfig, ParallelGardenersConfig,
)

# Build a Forest, then drive one cycle with mocked LLMs (replace with real ones in production).
# See examples/quick_start.py for a runnable end-to-end demo.
```

- `examples/quick_start.py` — end-to-end demo with mocked LLMs.
- `examples/bring_your_own_llm.py` — plug your own LLM SDK in via the framework's builders.
- `examples/write_your_own_domain.py` — template for a new market plugin (~150 lines).

## What's in here

| Module | What |
|---|---|
| `state` · `validate` · `classify` | Canonical state model + fail-loud validator + result classification |
| `weather` · `seeds` · `roles` · `events` · `handoff` | Per-cycle attention router, seed scoring/nursery, agent-attributed events, schema'd handoff protocol |
| `cycle` · `deliberation` · `trajectories` | The cycle driver, v2.0 multi-agent deliberation, v2.1 trajectory evolution primitives |
| `domain` | The `ResearchDomain` ABC + `cache_dir()` helper |
| `dsl.types` · `dsl.parser` · `dsl.evaluator` · `dsl.random_formula` | The DSL kit |
| `gates.factor_gates` · `gates.matched_random` · `gates.profiles` | The gates kit |
| `llm.protocols` · `llm.builders` · `llm.litellm_adapter` · `llm.mocks` | LLM-agnostic protocols + builders + reference adapter |
| `domains.demo` | Reference domain plugin using the kits |

## Rigor invariants (test-guarded)

1. **Gate completeness is a type invariant** — a result cannot classify as `fruit` without a
   complete `GateRecord` and `execution_mode == "tool_executed"`.
2. **Single writer** — `cycle.run_cycle` is the only forest-state mutator; deliberation and
   trajectory operators are pure (read-only on `Forest`).
3. **Different-model skeptic** — `make_llm_skeptic` refuses to run when its model family equals
   the gardener's.
4. **No fruit by lineage** — trajectory `mutate` / `crossover` produce children with
   `final_classification = None`; sick parents are excluded.
5. **No silent fallback** — LLM unavailability is always hard fail.

## License

MIT. See [`../LICENSE`](../LICENSE).
