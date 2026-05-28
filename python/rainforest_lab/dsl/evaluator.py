"""DSL evaluator — walks an AST, resolves fields against a panel, calls registered op fns."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

import pandas as pd

from rainforest_lab.dsl.parser import Node
from rainforest_lab.dsl.types import OpRegistry


def evaluate(node: Node, panel: pd.DataFrame, registry: OpRegistry) -> pd.Series:
    if node.kind == "field":
        return panel[node.name]
    if node.kind == "literal":
        # Literals are leaves; the parser only allows them as windowed-op last args.
        # An op invocation receives the literal value (int) directly, not via evaluate().
        raise ValueError("literals cannot appear as top-level evaluated nodes")
    # node.kind == "op"
    op = registry.get(node.name)
    args: list[Any] = []
    for child in node.children:
        if child.kind == "literal":
            args.append(child.value)
        else:
            args.append(evaluate(child, panel, registry))
    return cast(pd.Series, op.fn(*args))


def compile_node(node: Node, registry: OpRegistry) -> Callable[[pd.DataFrame], pd.Series]:
    """Return a closure that evaluates ``node`` against a panel. Useful as a
    ``ResearchDomain.compile_candidate`` return value."""

    def _run(panel: pd.DataFrame) -> pd.Series:
        return evaluate(node, panel, registry)

    return _run


__all__ = ["compile_node", "evaluate"]
