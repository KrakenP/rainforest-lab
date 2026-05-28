"""Domain-registered field + operator definitions for the rainforest DSL."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

OpKind = Literal["unary", "binary", "windowed"]


@dataclass(frozen=True)
class OpDef:
    """A registered operator. ``fn`` is invoked by the evaluator with arity-correct args."""

    name: str
    arity: int
    kind: OpKind
    fn: Callable[..., Any]
    valid_windows: tuple[int, ...] = ()  # only meaningful when kind == "windowed"


class OpRegistry:
    """Mutable registry of fields + operators that a domain plugin assembles at construction."""

    def __init__(self) -> None:
        self._ops: dict[str, OpDef] = {}
        self._fields: list[str] = []

    def register(self, op: OpDef) -> None:
        if op.name in self._ops:
            raise ValueError(f"operator {op.name!r} already registered")
        self._ops[op.name] = op

    def register_field(self, name: str) -> None:
        if name in self._fields:
            raise ValueError(f"field {name!r} already registered")
        self._fields.append(name)

    def get(self, name: str) -> OpDef:
        try:
            return self._ops[name]
        except KeyError as exc:
            raise KeyError(f"unknown operator {name!r}") from exc

    @property
    def ops(self) -> tuple[str, ...]:
        return tuple(self._ops.keys())

    @property
    def fields(self) -> tuple[str, ...]:
        return tuple(self._fields)


__all__ = ["OpDef", "OpKind", "OpRegistry"]
