from __future__ import annotations

import numpy as np

from rainforest_lab.dsl.parser import max_depth as ast_depth
from rainforest_lab.dsl.parser import parse
from rainforest_lab.dsl.random_formula import random_formula
from rainforest_lab.dsl.types import OpDef, OpRegistry


def _registry() -> OpRegistry:
    reg = OpRegistry()
    for fname in ("close", "volume"):
        reg.register_field(fname)
    reg.register(OpDef("cs_rank", 1, "unary", lambda s: s))
    reg.register(OpDef("add", 2, "binary", lambda a, b: a + b))
    reg.register(OpDef("ts_mean", 2, "windowed", lambda s, n: s, valid_windows=(3, 5)))
    return reg


def test_random_formula_is_parseable() -> None:
    rng = np.random.default_rng(0)
    reg = _registry()
    formula = random_formula(rng, reg, max_depth=2)
    parse(formula, reg)  # round-trip: must parse without error


def test_random_formula_is_deterministic_for_same_seed() -> None:
    reg = _registry()
    a = random_formula(np.random.default_rng(42), reg, max_depth=2)
    b = random_formula(np.random.default_rng(42), reg, max_depth=2)
    assert a == b


def test_random_formula_respects_max_depth() -> None:
    rng = np.random.default_rng(1)
    reg = _registry()
    for _ in range(20):
        formula = random_formula(rng, reg, max_depth=3)
        node = parse(formula, reg)
        assert ast_depth(node) <= 3
