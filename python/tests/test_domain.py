from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd

from rainforest_lab.domain import (
    AlignRequest,
    DomainData,
    FeatureSpace,
    ResearchDomain,
    Threshold,
    gate_record_complete,
)
from rainforest_lab.state import GateDef, GateRecord


class _StubDomain(ResearchDomain):
    name = "stub"

    def feature_space(self) -> FeatureSpace:
        return FeatureSpace(columns=[], operators=[])

    def load_data(self) -> DomainData:
        raise NotImplementedError

    def data_readiness(self) -> dict[str, bool]:
        return {}

    def compile_candidate(self, formula: str) -> Callable[[pd.DataFrame], pd.Series]:
        raise NotImplementedError

    def gate_spec(self) -> list[GateDef]:
        return []

    def evaluate(
        self,
        compiled: Callable[[pd.DataFrame], pd.Series],
        run_id: str,
        promoted_pool: dict[str, pd.Series],
    ) -> GateRecord:
        raise NotImplementedError

    def matched_random_threshold(self, tier: str) -> Threshold:
        raise NotImplementedError

    def novelty_corr(self, sig: pd.Series, other: pd.Series) -> float:
        return 0.0

    def align_request(
        self, factor_id: str, mechanism: str, evidence: dict[str, Any]
    ) -> AlignRequest:
        raise NotImplementedError


def test_align_request_carries_rubric_and_schema() -> None:
    req = AlignRequest(
        factor_id="f1",
        mechanism="m",
        evidence={"sharpe": 1.0},
        rubric="0-3 scale",
        schema={"type": "object"},
    )
    assert req.rubric == "0-3 scale"
    assert req.schema["type"] == "object"


def test_threshold_carries_value_and_provenance() -> None:
    t = Threshold(value=0.9, provenance={"N": 1000, "percentile": 99})
    assert t.value == 0.9 and t.provenance["N"] == 1000


def test_gate_record_complete_true_false() -> None:
    spec = [
        GateDef(name="g1", hard=True),
        GateDef(name="g2", hard=True),
        GateDef(name="g7", hard=False, needs_handoff=True),
    ]
    missing = GateRecord(
        domain="demo",
        factor_id="factor_1",
        gates={"g1": {"passed": True}, "g7": {"score": 2, "passed": True}},
        execution_mode="tool_executed",
    )
    full = GateRecord(
        domain="demo",
        factor_id="factor_1",
        gates={
            "g1": {"passed": True},
            "g2": {"passed": True},
            "g7": {"score": 2, "passed": True},
        },
        execution_mode="tool_executed",
    )
    assert gate_record_complete(missing, spec) is False
    assert gate_record_complete(full, spec) is True


def test_domain_cache_dir_defaults_under_cwd(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    d = _StubDomain().cache_dir()
    assert d == tmp_path / "runs" / "stub" / "cache"
    assert d.exists()


def test_domain_cache_dir_honours_root(tmp_path: Path) -> None:
    d = _StubDomain().cache_dir(root=tmp_path / "custom")
    assert d == tmp_path / "custom" / "runs" / "stub" / "cache"
    assert d.exists()


def test_domain_cache_dir_idempotent(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    a = _StubDomain().cache_dir()
    b = _StubDomain().cache_dir()
    assert a == b
