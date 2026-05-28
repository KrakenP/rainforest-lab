"""Template: implement ResearchDomain for your own market using dsl + gates kits.

This file is a self-contained sketch; copy + fill in the data-loading specifics for your market.
For the canonical reference implementation see ``rainforest_lab/domains/demo.py``.

Required pieces:
1. An ``OpRegistry`` that lists your market's fields + operators.
2. A YAML gates profile with the threshold for each gate.
3. A ``ResearchDomain`` subclass that wires (1) + (2) into the engine.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd

from rainforest_lab import (
    AlignRequest,
    DomainData,
    FeatureSpace,
    GateDef,
    GateRecord,
    OpDef,
    OpRegistry,
    ResearchDomain,
    Threshold,
    compile_node,
    load_gates_profile,
    parse,
)


def _build_registry() -> OpRegistry:
    """Register the fields + operators your market needs."""
    reg = OpRegistry()
    for field in ("close", "volume", "your_field"):
        reg.register_field(field)
    reg.register(OpDef("cs_rank", 1, "unary", lambda s: s.rank(pct=True)))
    reg.register(OpDef(
        "ts_mean", 2, "windowed",
        lambda s, n: s.groupby(level="symbol").rolling(n).mean().droplevel(0),
        valid_windows=(3, 5, 10),
    ))
    # Add the operators your market needs.
    return reg


class MyDomain(ResearchDomain):
    """Replace this with your market's plugin."""

    name = "my_market"

    def __init__(self) -> None:
        self._registry = _build_registry()
        profile_path = Path(__file__).parent / "my_market_gates.yaml"
        self._gates = load_gates_profile(profile_path) if profile_path.exists() else {}

    def feature_space(self) -> FeatureSpace:
        return FeatureSpace(
            columns=list(self._registry.fields), operators=list(self._registry.ops)
        )

    def load_data(self) -> DomainData:
        # Load your market's data here. Apply PIT discipline, survivorship filters, adjustments.
        # Return DomainData(panel, train_panel, oos_panel, fwd_train, fwd_oos).
        raise NotImplementedError("provide your market's data loader")

    def data_readiness(self) -> dict[str, bool]:
        data = self.load_data()
        return {"panel": not data.panel.empty}

    def compile_candidate(self, formula: str) -> Callable[[pd.DataFrame], pd.Series]:
        return compile_node(parse(formula, self._registry), self._registry)

    def gate_spec(self) -> list[GateDef]:
        return [
            GateDef(name="g1_sanity", hard=True, needs_handoff=False),
            GateDef(name="g5_turnover", hard=True, needs_handoff=False),
            GateDef(name="g8_decay", hard=True, needs_handoff=False),
            GateDef(name="g9_liquidity", hard=True, needs_handoff=False),
            GateDef(name="alignment", hard=False, needs_handoff=True),
        ]

    def evaluate(
        self,
        compiled: Callable[[pd.DataFrame], pd.Series],
        run_id: str,
        promoted_pool: dict[str, pd.Series],
    ) -> GateRecord:
        data = self.load_data()
        signal = compiled(data.oos_panel)
        fwd = data.fwd_oos.reindex(signal.index).fillna(0.0)
        return GateRecord(
            domain=self.name,
            factor_id=run_id,
            execution_mode="tool_executed",
            gates={
                "g1_sanity":   self._gates["g1_sanity"](signal),
                "g5_turnover": self._gates["g5_turnover"](signal),
                "g8_decay":    self._gates["g8_decay"](signal, fwd),
                "g9_liquidity": self._gates["g9_liquidity"](signal, data.panel["volume"]),
                "alignment":   {"passed": True, "score": 2, "value": 2, "threshold": 1,
                                "detail": "set by handoff"},
            },
        )

    def matched_random_threshold(self, tier: str) -> Threshold:
        # Use rainforest_lab.matched_random_threshold once at grounding to freeze your P99 bar,
        # cache it in a YAML, and return it from here.
        raise NotImplementedError("freeze your matched_random bar at grounding")

    def novelty_corr(self, sig: pd.Series, other: pd.Series) -> float:
        aligned = pd.concat([sig.rename("sig"), other.rename("other")], axis=1).dropna()
        if aligned.empty:
            return 0.0
        corr = aligned["sig"].corr(aligned["other"])
        return 0.0 if pd.isna(corr) else float(corr)

    def align_request(
        self, factor_id: str, mechanism: str, evidence: dict[str, Any]
    ) -> AlignRequest:
        return AlignRequest(
            factor_id=factor_id, mechanism=mechanism, evidence=evidence,
            rubric="Score 0-3 whether evidence supports the mechanism.",
            schema={
                "type": "object",
                "required": ["score", "reason"],
                "properties": {
                    "score": {"type": "integer", "minimum": 0, "maximum": 3},
                    "reason": {"type": "string"},
                },
            },
        )


# Companion YAML file (sibling to this example):
#
#   # my_market_gates.yaml
#   g1_sanity:   {nan_max: 0.30}
#   g5_turnover: {turnover_max: 0.40}
#   g8_decay:    {max_decay_slope: 0.0, fee_bp: 8.54, periods_per_year: 12.0}
#   g9_liquidity: {min_adv: 100000.0}
