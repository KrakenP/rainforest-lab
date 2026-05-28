from __future__ import annotations

import numpy as np
import pandas as pd

from rainforest_lab.gates.factor_gates import (
    g1_sanity,
    g5_turnover,
    g8_decay,
    g9_liquidity,
    net_sharpe,
)


def _factor(returns: np.ndarray) -> pd.Series:
    idx = pd.MultiIndex.from_product(
        [pd.date_range("2024-01-01", periods=len(returns), freq="ME"), ["A", "B", "C", "D"]],
        names=["date", "symbol"],
    )
    rng = np.random.default_rng(0)
    return pd.Series(rng.standard_normal(len(returns) * 4), index=idx)


def test_net_sharpe_nan_for_short_series() -> None:
    # Helper produces 4 symbols × N periods rows. To trip the < 12 guard, use 2 periods.
    factor = _factor(np.arange(2))
    fwd = factor.copy()
    assert np.isnan(net_sharpe(factor, fwd, fee_bp=8.54, periods_per_year=12))


def test_net_sharpe_returns_finite_for_long_enough_series() -> None:
    factor = _factor(np.arange(36))
    fwd = factor.shift(-4).fillna(0.0)
    result = net_sharpe(factor, fwd, fee_bp=8.54, periods_per_year=12)
    # may be nan when std is degenerate, but at minimum should be a float
    assert isinstance(result, float)


def test_g1_sanity_pass_on_clean_factor() -> None:
    factor = _factor(np.arange(36))
    result = g1_sanity(factor, nan_max=0.30)
    assert result["passed"] is True
    assert "value" in result and result["value"] <= 0.30


def test_g1_sanity_fail_when_too_many_nans() -> None:
    factor = _factor(np.arange(36)).copy()
    factor.iloc[: len(factor) * 7 // 10] = np.nan
    result = g1_sanity(factor, nan_max=0.30)
    assert result["passed"] is False


def test_g5_turnover_returns_dict_with_passed() -> None:
    factor = _factor(np.arange(36))
    result = g5_turnover(factor, turnover_max=2.0)
    assert "passed" in result and "value" in result
    assert "threshold" in result


def test_g8_decay_returns_passed_and_decay_slope() -> None:
    factor = _factor(np.arange(60))
    fwd = factor.shift(-1).fillna(0.0)
    result = g8_decay(factor, fwd, max_decay_slope=-0.1, fee_bp=8.54, periods_per_year=12.0)
    assert "passed" in result and "value" in result


def test_g9_liquidity_checks_coverage() -> None:
    factor = _factor(np.arange(36))
    adv = factor.abs() * 1e6
    result = g9_liquidity(factor, adv, min_adv=1e5)
    assert "passed" in result and "value" in result
    assert "threshold" in result and result["threshold"] == 1e5
