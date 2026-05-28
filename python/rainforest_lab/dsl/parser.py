"""Formula parser for the rainforest DSL.

Grammar (informal):
    formula  := op_name "(" arg ("," arg)* ")" | field | literal
    arg      := formula | literal
    literal  := signed integer
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from rainforest_lab.dsl.types import OpRegistry

NodeKind = Literal["op", "field", "literal"]


@dataclass(frozen=True)
class Node:
    """An AST node. Either an op (with children), a field reference, or an integer literal."""

    kind: NodeKind
    name: str = ""
    value: int | None = None
    children: tuple[Node, ...] = field(default_factory=tuple)


def parse(formula: str, registry: OpRegistry) -> Node:
    """Parse a formula string into a Node. Raises KeyError on unknown op, ValueError on bad
    field/window."""

    text = formula.strip()
    if not text:
        raise ValueError("empty formula")

    # Field?
    if text in registry.fields:
        return Node(kind="field", name=text)

    # Literal?
    if _is_signed_int(text):
        return Node(kind="literal", value=int(text))

    # Must be op(...)
    open_paren = text.find("(")
    if open_paren < 0 or not text.endswith(")"):
        raise ValueError(f"not a field, literal, or op call: {formula!r}")
    op_name = text[:open_paren]
    op = registry.get(op_name)  # raises KeyError on unknown
    inner = text[open_paren + 1 : -1]
    arg_strs = _split_args(inner)
    if len(arg_strs) != op.arity:
        raise ValueError(
            f"op {op_name!r} expects {op.arity} arg(s); got {len(arg_strs)}"
        )
    children = tuple(parse(arg, registry) for arg in arg_strs)
    if op.kind == "windowed":
        last = children[-1]
        if last.kind != "literal" or last.value not in op.valid_windows:
            raise ValueError(
                f"op {op_name!r} window must be in {op.valid_windows}; got {last}"
            )
    return Node(kind="op", name=op_name, children=children)


def _split_args(inner: str) -> list[str]:
    """Split a comma-separated argument list, respecting parenthesis depth."""
    args: list[str] = []
    depth = 0
    buf: list[str] = []
    for ch in inner:
        if ch == "(":
            depth += 1
            buf.append(ch)
        elif ch == ")":
            depth -= 1
            if depth < 0:
                raise ValueError("unbalanced parentheses")
            buf.append(ch)
        elif ch == "," and depth == 0:
            args.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if depth != 0:
        raise ValueError("unbalanced parentheses")
    tail = "".join(buf).strip()
    if tail:
        args.append(tail)
    return args


def _is_signed_int(text: str) -> bool:
    return text.lstrip("-").isdigit() and len(text.lstrip("-")) > 0


def max_depth(node: Node) -> int:
    if node.kind != "op":
        return 0
    return 1 + max((max_depth(child) for child in node.children), default=0)


def collect_fields(node: Node) -> list[str]:
    """Return the set of field names referenced (deduplicated, stable order of first sight)."""
    out: list[str] = []
    seen: set[str] = set()
    _walk_fields(node, out, seen)
    return out


def _walk_fields(node: Node, out: list[str], seen: set[str]) -> None:
    if node.kind == "field" and node.name not in seen:
        seen.add(node.name)
        out.append(node.name)
    for child in node.children:
        _walk_fields(child, out, seen)


def complexity_tier(node: Node) -> Literal["simple", "medium", "complex"]:
    """Map AST depth to a coarse complexity tier."""
    depth = max_depth(node)
    if depth <= 1:
        return "simple"
    if depth == 2:
        return "medium"
    return "complex"


__all__ = ["Node", "collect_fields", "complexity_tier", "max_depth", "parse"]
