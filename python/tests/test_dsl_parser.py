from __future__ import annotations

import pytest

from rainforest_lab.dsl.parser import (
    Node,
    collect_fields,
    max_depth,
    parse,
)
from rainforest_lab.dsl.types import OpDef, OpRegistry


def _basic_registry() -> OpRegistry:
    reg = OpRegistry()
    for fname in ("close", "volume", "open"):
        reg.register_field(fname)
    reg.register(OpDef("cs_rank", 1, "unary", lambda s: s))
    reg.register(OpDef("ts_mean", 2, "windowed", lambda s, n: s, valid_windows=(3, 5, 10)))
    reg.register(OpDef("add", 2, "binary", lambda a, b: a + b))
    return reg


def test_parse_field_reference() -> None:
    node = parse("close", _basic_registry())
    assert isinstance(node, Node)
    assert node.kind == "field" and node.name == "close"


def test_parse_unary() -> None:
    node = parse("cs_rank(close)", _basic_registry())
    assert node.name == "cs_rank" and len(node.children) == 1
    assert node.children[0].name == "close"


def test_parse_nested() -> None:
    node = parse("cs_rank(ts_mean(close, 5))", _basic_registry())
    assert node.name == "cs_rank"
    inner = node.children[0]
    assert inner.name == "ts_mean" and len(inner.children) == 2
    assert inner.children[1].kind == "literal" and inner.children[1].value == 5


def test_parse_unknown_op_raises() -> None:
    with pytest.raises(KeyError, match="frobnicate"):
        parse("frobnicate(close)", _basic_registry())


def test_parse_unknown_field_raises() -> None:
    with pytest.raises(ValueError, match="bogus_field"):
        parse("bogus_field", _basic_registry())


def test_parse_invalid_window_raises() -> None:
    with pytest.raises(ValueError, match="window"):
        parse("ts_mean(close, 7)", _basic_registry())


def test_max_depth() -> None:
    assert max_depth(parse("close", _basic_registry())) == 0
    assert max_depth(parse("cs_rank(close)", _basic_registry())) == 1
    assert max_depth(parse("cs_rank(ts_mean(close, 5))", _basic_registry())) == 2


def test_collect_fields() -> None:
    node = parse("add(cs_rank(close), ts_mean(volume, 3))", _basic_registry())
    assert set(collect_fields(node)) == {"close", "volume"}
