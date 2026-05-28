"""Random formula generator — used by ``matched_random`` and by exploratory mining."""

from __future__ import annotations

import numpy as np

from rainforest_lab.dsl.types import OpRegistry


def random_formula(rng: np.random.Generator, registry: OpRegistry, *, max_depth: int = 2) -> str:
    """Generate a random formula string parseable against ``registry``. Bounded by ``max_depth``."""

    if max_depth < 0:
        raise ValueError("max_depth must be non-negative")
    return _random_node(rng, registry, depth=0, max_depth=max_depth)


def _random_node(
    rng: np.random.Generator, reg: OpRegistry, *, depth: int, max_depth: int
) -> str:
    if depth >= max_depth or not reg.ops or rng.random() < 0.30:
        # leaf: pick a field
        if not reg.fields:
            raise ValueError("registry has no fields")
        return str(rng.choice(reg.fields))
    op_name = str(rng.choice(reg.ops))
    op = reg.get(op_name)
    children = []
    for slot in range(op.arity):
        if op.kind == "windowed" and slot == op.arity - 1:
            window = int(rng.choice(op.valid_windows))
            children.append(str(window))
        else:
            children.append(_random_node(rng, reg, depth=depth + 1, max_depth=max_depth))
    return f"{op_name}({', '.join(children)})"


__all__ = ["random_formula"]
