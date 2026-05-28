"""Matched-random significance bar (G3) — P{percentile} of OOS Sharpe over N random factors.

The function is domain-agnostic: ``evaluate`` is a user-supplied callable that takes a formula
string and returns its OOS Sharpe (or any scalar performance metric). The framework supplies the
random formula generation, draws the empirical distribution, and freezes the percentile threshold
with provenance metadata so it can be archived and re-used."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np

from rainforest_lab.dsl.random_formula import random_formula
from rainforest_lab.dsl.types import OpRegistry


def matched_random_threshold(
    registry: OpRegistry,
    evaluate: Callable[[str], float],
    *,
    n: int,
    percentile: float,
    seed: int,
    provenance: dict[str, Any],
    max_depth: int = 2,
) -> dict[str, Any]:
    """Sample N random formulas, evaluate each, return the percentile threshold + provenance.

    Provenance carries enough metadata (``N``, ``percentile``, ``seed``, plus any caller-supplied
    keys like ``date`` / ``universe`` / ``tier``) that the threshold can be re-derived later."""

    if n < 1:
        raise ValueError("n must be positive")
    if not (0 < percentile <= 100):
        raise ValueError("percentile must be in (0, 100]")

    rng = np.random.default_rng(seed)
    samples = np.empty(n, dtype=float)
    for i in range(n):
        formula = random_formula(rng, registry, max_depth=max_depth)
        samples[i] = float(evaluate(formula))

    threshold = float(np.percentile(samples, percentile))
    return {
        "value": threshold,
        "provenance": {
            **provenance,
            "N": n,
            "percentile": percentile,
            "seed": seed,
        },
        "samples_summary": {
            "min": float(samples.min()),
            "max": float(samples.max()),
            "mean": float(samples.mean()),
            "median": float(np.median(samples)),
        },
    }


__all__ = ["matched_random_threshold"]
