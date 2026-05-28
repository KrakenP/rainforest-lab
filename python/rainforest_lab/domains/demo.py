"""DemoDomain — synthetic reference plugin that doubles as the 'how to write your own' template.

It registers a minimal field/op vocabulary, supplies a tiny gates profile, and exposes the
``ResearchDomain`` interface end-to-end. Reading this file should be enough to write a domain
plugin against your own market."""

from __future__ import annotations

import random
from collections.abc import Callable
from typing import Any

import pandas as pd

from rainforest_lab.domain import (
    AlignRequest,
    DomainData,
    FeatureSpace,
    ResearchDomain,
    Threshold,
)
from rainforest_lab.dsl.evaluator import compile_node
from rainforest_lab.dsl.parser import parse
from rainforest_lab.dsl.types import OpDef, OpRegistry
from rainforest_lab.state import GateDef, GateRecord


def _build_registry() -> OpRegistry:
    reg = OpRegistry()
    for col in ("close", "open", "high", "low", "volume", "return_1d"):
        reg.register_field(col)

    def _momentum(close: pd.Series, n: int) -> pd.Series:
        return close.groupby(level="symbol").pct_change(n).fillna(0.0)

    def _reversal(close: pd.Series, n: int) -> pd.Series:
        return -close.groupby(level="symbol").pct_change(n).fillna(0.0)

    reg.register(OpDef("momentum", 2, "windowed", _momentum, valid_windows=(3, 5, 10)))
    reg.register(OpDef("reversal", 2, "windowed", _reversal, valid_windows=(3, 5, 10)))
    return reg


class DemoDomain(ResearchDomain):
    """Synthetic DemoDomain. Use as a template for your own domain plugin."""

    name = "demo"

    def __init__(self, *, seed: int = 15) -> None:
        self.seed = seed
        self._data: DomainData | None = None
        self._registry: OpRegistry = _build_registry()

    def feature_space(self) -> FeatureSpace:
        return FeatureSpace(
            columns=list(self._registry.fields), operators=list(self._registry.ops)
        )

    def load_data(self) -> DomainData:
        if self._data is None:
            self._data = self._build_data()
        return self._data

    def data_readiness(self) -> dict[str, bool]:
        data = self.load_data()
        return {
            "panel": not data.panel.empty,
            "train": not data.train_panel.empty and not data.fwd_train.empty,
            "oos": not data.oos_panel.empty and not data.fwd_oos.empty,
        }

    def compile_candidate(self, formula: str) -> Callable[[pd.DataFrame], pd.Series]:
        # Accept both AST formulas (`momentum(close, 5)`) and legacy sugar (`momentum:5`).
        if ":" in formula and "(" not in formula:
            op_name, window = formula.split(":", 1)
            formula = f"{op_name}(close, {int(window)})"
        node = parse(formula, self._registry)
        return compile_node(node, self._registry)

    def gate_spec(self) -> list[GateDef]:
        return [
            GateDef(name="coverage", hard=True, needs_handoff=False),
            GateDef(name="edge", hard=True, needs_handoff=False),
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
        coverage = float(signal.notna().mean()) if len(signal) else 0.0
        edge = float((signal.fillna(0.0) * fwd).mean())
        novelty = self._max_abs_corr(signal, promoted_pool)
        return GateRecord(
            domain=self.name,
            factor_id=run_id,
            execution_mode="tool_executed",
            gates={
                "coverage": {
                    "passed": coverage >= 0.9,
                    "value": coverage,
                    "threshold": 0.9,
                    "detail": "non-null signal share",
                },
                "edge": {
                    "passed": edge > -0.001,
                    "value": edge,
                    "threshold": -0.001,
                    "detail": "mean signal * one-step forward return",
                },
                "alignment": {
                    "passed": True,
                    "score": 2,
                    "value": 2,
                    "threshold": 1,
                    "detail": f"template handoff score; max promoted corr={novelty:.3f}",
                },
            },
        )

    def matched_random_threshold(self, tier: str) -> Threshold:
        return Threshold(
            value=0.0,
            provenance={
                "percentile": 95,
                "N": 100,
                "universe": "demo_10x120",
                "date": "2024-01-01",
                "tier": tier,
            },
        )

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
            factor_id=factor_id,
            mechanism=mechanism,
            evidence=evidence,
            rubric="Score whether evidence supports the stated mechanism on a 0-3 scale.",
            schema={
                "type": "object",
                "required": ["score", "reason"],
                "properties": {
                    "score": {"type": "integer", "minimum": 0, "maximum": 3},
                    "reason": {"type": "string"},
                },
            },
        )

    def _max_abs_corr(self, sig: pd.Series, promoted_pool: dict[str, pd.Series]) -> float:
        if not promoted_pool:
            return 0.0
        return max(abs(self.novelty_corr(sig, other)) for other in promoted_pool.values())

    def _build_data(self) -> DomainData:
        rng = random.Random(self.seed)
        dates = pd.date_range("2024-01-01", periods=120, freq="D", name="date")
        symbols = [f"S{i:02d}" for i in range(10)]
        records: list[dict[str, Any]] = []
        for sym_idx, symbol in enumerate(symbols):
            close = 100.0 + sym_idx
            for d in dates:
                shock = rng.uniform(-0.02, 0.02)
                drift = 0.0005 * ((sym_idx % 3) - 1)
                close *= 1.0 + drift + shock
                records.append({
                    "date": d, "symbol": symbol, "close": close,
                    "open": close, "high": close, "low": close,
                    "volume": 1_000_000 + rng.randint(0, 50_000),
                })
        panel = (
            pd.DataFrame.from_records(records).set_index(["date", "symbol"]).sort_index()
        )
        panel["return_1d"] = panel["close"].groupby(level="symbol").pct_change().fillna(0.0)
        fwd = panel["return_1d"].groupby(level="symbol").shift(-1).fillna(0.0)
        train_dates = dates[:90]
        oos_dates = dates[90:]
        train_mask = panel.index.get_level_values("date").isin(train_dates)
        oos_mask = panel.index.get_level_values("date").isin(oos_dates)
        return DomainData(
            panel=panel,
            train_panel=panel.loc[train_mask],
            oos_panel=panel.loc[oos_mask],
            fwd_train=fwd.loc[train_mask],
            fwd_oos=fwd.loc[oos_mask],
        )


__all__ = ["DemoDomain"]
