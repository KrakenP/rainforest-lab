from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from rainforest_lab.dsl.evaluator import compile_node, evaluate
from rainforest_lab.dsl.parser import parse
from rainforest_lab.dsl.types import OpDef, OpRegistry


def _panel() -> pd.DataFrame:
    idx = pd.MultiIndex.from_product(
        [pd.date_range("2024-01-01", periods=10, freq="D"), ["A", "B"]],
        names=["date", "symbol"],
    )
    return pd.DataFrame({
        "close": np.arange(20, dtype=float),
        "volume": np.arange(20, dtype=float) + 100,
    }, index=idx)


def _registry() -> OpRegistry:
    reg = OpRegistry()
    reg.register_field("close")
    reg.register_field("volume")
    reg.register(OpDef("add", 2, "binary", lambda a, b: a + b))
    reg.register(OpDef("neg", 1, "unary", lambda s: -s))
    reg.register(OpDef(
        "ts_mean", 2, "windowed",
        lambda s, n: s.groupby(level="symbol").transform(lambda g: g.rolling(n).mean()),
        valid_windows=(2, 3),
    ))
    return reg


def test_evaluate_field() -> None:
    out = evaluate(parse("close", _registry()), _panel(), _registry())
    pd.testing.assert_series_equal(out, _panel()["close"])


def test_evaluate_unary() -> None:
    out = evaluate(parse("neg(close)", _registry()), _panel(), _registry())
    pd.testing.assert_series_equal(out, -_panel()["close"])


def test_evaluate_binary() -> None:
    out = evaluate(parse("add(close, volume)", _registry()), _panel(), _registry())
    pd.testing.assert_series_equal(out, _panel()["close"] + _panel()["volume"])


def test_evaluate_windowed() -> None:
    out = evaluate(parse("ts_mean(close, 2)", _registry()), _panel(), _registry())
    assert out.notna().any()
    # rolling(2) leaves the first per-symbol value NaN
    assert out.groupby(level="symbol").apply(lambda g: g.iloc[0]).isna().all()


def test_compile_node_returns_callable() -> None:
    reg = _registry()
    fn = compile_node(parse("add(close, volume)", reg), reg)
    out = fn(_panel())
    pd.testing.assert_series_equal(out, _panel()["close"] + _panel()["volume"])


def test_evaluate_unknown_field_raises() -> None:
    # Field is registered at parse time; corruption at runtime (missing column) shows up here.
    reg = _registry()
    node = parse("close", reg)
    bad_panel = _panel().drop(columns=["close"])
    with pytest.raises(KeyError):
        evaluate(node, bad_panel, reg)
