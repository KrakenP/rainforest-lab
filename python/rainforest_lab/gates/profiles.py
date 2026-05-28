"""Gates profile YAML loader — returns a dict of preconfigured gate callables.

A profile YAML looks like::

    net_sharpe:   {fee_bp: 8.54, periods_per_year: 12}
    g1_sanity:    {nan_max: 0.30}
    g5_turnover:  {turnover_max: 0.40}
    g8_decay:     {max_decay_slope: 0.0}
    g9_liquidity: {min_adv: 100000.0}

The loaded callables already have their thresholds bound; a domain plugin can call
``profile["g1_sanity"](factor)`` directly during ``evaluate()``."""

from __future__ import annotations

from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import Any

import yaml

from rainforest_lab.gates.factor_gates import (
    g1_sanity,
    g5_turnover,
    g8_decay,
    g9_liquidity,
    net_sharpe,
)

_GATE_TABLE: dict[str, Callable[..., Any]] = {
    "net_sharpe": net_sharpe,
    "g1_sanity": g1_sanity,
    "g5_turnover": g5_turnover,
    "g8_decay": g8_decay,
    "g9_liquidity": g9_liquidity,
}


def load_gates_profile(path: Path) -> dict[str, Callable[..., Any]]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    out: dict[str, Callable[..., Any]] = {}
    for gate_name, params in data.items():
        if gate_name not in _GATE_TABLE:
            raise ValueError(
                f"unknown gate {gate_name!r} in profile; "
                f"valid gates: {sorted(_GATE_TABLE.keys())}"
            )
        if params is None:
            params = {}
        if not isinstance(params, dict):
            raise ValueError(f"gate {gate_name!r} params must be a mapping; got {type(params)}")
        out[gate_name] = partial(_GATE_TABLE[gate_name], **params)
    return out


__all__ = ["load_gates_profile"]
