"""Parameterized factor gates — usable across markets (A-share monthly, crypto-perp 1h, US daily…).

Every market-specific threshold is a keyword argument with no opinionated default. Each gate
function returns a dict with at minimum ``{"passed": bool, "value": float, "threshold": float,
"detail": str}`` so the dict can drop into a ``GateRecord.gates`` entry directly."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def _cross_section_weights(g: pd.DataFrame) -> pd.Series:
    """Cross-sectional z-score weights scaled to unit gross exposure."""
    f = g["f"]
    mu, sigma = f.mean(), f.std()
    if sigma < 1e-8:
        return pd.Series(0.0, index=g.index)
    w = (f - mu) / sigma
    abs_sum = w.abs().sum()
    return w / abs_sum if abs_sum > 1e-8 else w


def net_sharpe(
    factor: pd.Series,
    fwd_ret: pd.Series,
    *,
    fee_bp: float,
    periods_per_year: float,
) -> float:
    """Annualised net Sharpe for a long-short z-scored portfolio with turnover-based fees.

    ``fee_bp`` and ``periods_per_year`` are required so the function stays market-agnostic
    (monthly A-share defaults differ from daily US-equity from 1h crypto-perp)."""

    aligned = pd.DataFrame({"f": factor, "r": fwd_ret}).dropna()
    if len(aligned) < 12:
        return float("nan")

    weights = aligned.groupby(level="date", group_keys=False).apply(_cross_section_weights)
    gross = (weights * aligned["r"]).groupby(level="date").sum()

    w_wide = weights.unstack(level="symbol").sort_index()
    turnover = w_wide.diff().abs().sum(axis=1).fillna(0.0)  # type: ignore[arg-type]
    net = gross - turnover.reindex(gross.index).fillna(0.0) * (fee_bp / 1e4)

    if net.empty or net.std() < 1e-10:
        return float("nan")
    return float(net.mean() / net.std() * math.sqrt(periods_per_year))


def g1_sanity(factor: pd.Series, *, nan_max: float = 0.30) -> dict[str, Any]:
    """Factor quality: NaN ratio bounded, no inf, not constant cross-sectionally."""

    checks: dict[str, dict[str, Any]] = {}

    nan_ratio = float(factor.isna().mean())
    checks["nan_ratio"] = {
        "passed": nan_ratio <= nan_max,
        "value": nan_ratio,
        "threshold": nan_max,
    }

    has_inf = bool(np.isinf(factor.dropna()).any())
    checks["no_inf"] = {"passed": not has_inf, "value": not has_inf}

    def _cross_std(g: pd.Series) -> float:
        return float(g.std())

    cross_stds = factor.groupby(level="date").apply(_cross_std)
    constant_sections = float((cross_stds < 1e-8).mean())
    checks["not_constant"] = {
        "passed": constant_sections < 0.5,
        "value": constant_sections,
        "threshold": 0.5,
    }

    failed = [k for k, v in checks.items() if not v["passed"]]
    return {
        "passed": len(failed) == 0,
        "value": float(nan_ratio),
        "threshold": float(nan_max),
        "detail": "sanity checks: nan_ratio + no_inf + not_constant",
        "failed_check": failed[0] if failed else None,
        "checks": checks,
    }


def g5_turnover(factor: pd.Series, *, turnover_max: float) -> dict[str, Any]:
    """Per-period portfolio turnover (sum of absolute weight changes) ≤ ``turnover_max``."""

    aligned = factor.dropna().to_frame("f")
    if aligned.empty:
        return {
            "passed": False,
            "value": float("nan"),
            "threshold": float(turnover_max),
            "detail": "no factor values to evaluate",
        }

    weights = aligned.groupby(level="date", group_keys=False).apply(_cross_section_weights)
    w_wide = weights.unstack(level="symbol").sort_index()
    monthly_turnover = w_wide.diff().abs().sum(axis=1).fillna(0.0)  # type: ignore[arg-type]
    avg_turnover = float(monthly_turnover.mean())

    return {
        "passed": math.isfinite(avg_turnover) and avg_turnover <= turnover_max,
        "value": avg_turnover,
        "threshold": float(turnover_max),
        "detail": "mean cross-sectional weight-change magnitude per period",
    }


def g8_decay(
    factor: pd.Series,
    fwd_ret: pd.Series,
    *,
    max_decay_slope: float,
    fee_bp: float = 0.0,
    periods_per_year: float = 12.0,
    half_window: int = 6,
) -> dict[str, Any]:
    """Rolling-Sharpe regression slope ≥ ``max_decay_slope`` (signal is not decaying too fast).

    Computes net Sharpe over a rolling window (default 6 periods), fits a linear regression vs
    time, and asserts the slope is at least ``max_decay_slope`` (which is normally a small negative
    number or zero)."""

    aligned = pd.DataFrame({"f": factor, "r": fwd_ret}).dropna()
    if len(aligned) < half_window * 3:
        return {
            "passed": False,
            "value": float("nan"),
            "threshold": float(max_decay_slope),
            "detail": "insufficient data",
        }

    weights = aligned.groupby(level="date", group_keys=False).apply(_cross_section_weights)
    gross = (weights * aligned["r"]).groupby(level="date").sum().sort_index()
    w_wide = weights.unstack(level="symbol").sort_index()
    turnover = w_wide.diff().abs().sum(axis=1).fillna(0.0)  # type: ignore[arg-type]
    net = (gross - turnover.reindex(gross.index).fillna(0.0) * (fee_bp / 1e4)).dropna()

    if len(net) < half_window * 2:
        return {
            "passed": True,
            "value": 0.0,
            "threshold": float(max_decay_slope),
            "detail": "too few periods for rolling check (vacuously pass)",
        }

    def _sharpe(x: np.ndarray) -> float:
        if len(x) < 3 or np.std(x) < 1e-10:
            return float("nan")
        return float(np.mean(x) / np.std(x) * math.sqrt(periods_per_year))

    rolling = (
        net.rolling(half_window, min_periods=half_window).apply(_sharpe, raw=True).dropna()
    )

    if len(rolling) < 3:
        return {
            "passed": True,
            "value": 0.0,
            "threshold": float(max_decay_slope),
            "detail": "too few windows (vacuously pass)",
        }

    x = np.arange(len(rolling), dtype=float)
    y = rolling.to_numpy().astype(float)
    valid = ~np.isnan(y)
    if valid.sum() < 3:
        return {
            "passed": True,
            "value": 0.0,
            "threshold": float(max_decay_slope),
            "detail": "too many NaN in rolling Sharpe (vacuously pass)",
        }
    slope = float(np.polyfit(x[valid], y[valid], 1)[0])

    return {
        "passed": slope >= max_decay_slope,
        "value": slope,
        "threshold": float(max_decay_slope),
        "detail": "linear regression slope of rolling-window Sharpe",
        "rolling_sharpe_last": float(rolling.iloc[-1]),
    }


def g9_liquidity(
    factor: pd.Series,
    adv: pd.Series,
    *,
    min_adv: float,
    pct: float = 0.20,
) -> dict[str, Any]:
    """Long-leg average daily volume (or analogous liquidity metric) at percentile ``pct`` ≥
    ``min_adv``.

    ``adv`` is a Series indexed by (date, symbol) — same as ``factor`` — giving the per-bar
    liquidity metric (mean daily volume in dollar terms, average daily turnover, ...). The exact
    metric is domain-defined; the gate just enforces the long-leg p20 floor."""

    def _long_leg(g: pd.Series) -> pd.Series:
        return g[g > g.mean()]

    long_factor = factor.groupby(level="date", group_keys=False).apply(_long_leg)
    long_adv = adv.reindex(long_factor.index).dropna()
    if long_adv.empty:
        return {
            "passed": False,
            "value": float("nan"),
            "threshold": float(min_adv),
            "detail": "no long-leg liquidity data",
        }

    p20 = float(long_adv.quantile(pct))
    return {
        "passed": p20 >= min_adv,
        "value": p20,
        "threshold": float(min_adv),
        "detail": f"long-leg liquidity at p{int(pct * 100)}",
        "pct": pct,
    }


__all__ = [
    "g1_sanity",
    "g5_turnover",
    "g8_decay",
    "g9_liquidity",
    "net_sharpe",
]
