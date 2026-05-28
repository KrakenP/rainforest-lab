from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from rainforest_lab.state import GateDef, GateRecord


@dataclass(frozen=True)
class DomainData:
    panel: pd.DataFrame
    train_panel: pd.DataFrame
    oos_panel: pd.DataFrame
    fwd_train: pd.Series
    fwd_oos: pd.Series


@dataclass(frozen=True)
class FeatureSpace:
    columns: list[str]
    operators: list[str]


@dataclass(frozen=True)
class Threshold:
    value: float
    provenance: dict[str, Any]


@dataclass(frozen=True)
class AlignRequest:
    factor_id: str
    mechanism: str
    evidence: dict[str, Any]
    rubric: str
    schema: dict[str, Any]


class ResearchDomain(ABC):
    name: str

    def cache_dir(self, root: Path | None = None) -> Path:
        """Default cache directory for this domain (overridable). Created on first call.

        Domain plugins should write panel caches, scratch artefacts, and any other
        domain-internal byproducts under here. The default is ``<cwd>/runs/<name>/cache``;
        pass an explicit ``root`` to relocate."""
        base = Path(root) if root else Path.cwd()
        path = base / "runs" / self.name / "cache"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @abstractmethod
    def feature_space(self) -> FeatureSpace:
        raise NotImplementedError

    @abstractmethod
    def load_data(self) -> DomainData:
        raise NotImplementedError

    @abstractmethod
    def data_readiness(self) -> dict[str, bool]:
        raise NotImplementedError

    @abstractmethod
    def compile_candidate(self, formula: str) -> Callable[[pd.DataFrame], pd.Series]:
        raise NotImplementedError

    @abstractmethod
    def gate_spec(self) -> list[GateDef]:
        raise NotImplementedError

    @abstractmethod
    def evaluate(
        self,
        compiled: Callable[[pd.DataFrame], pd.Series],
        run_id: str,
        promoted_pool: dict[str, pd.Series],
    ) -> GateRecord:
        raise NotImplementedError

    @abstractmethod
    def matched_random_threshold(self, tier: str) -> Threshold:
        raise NotImplementedError

    @abstractmethod
    def novelty_corr(self, sig: pd.Series, other: pd.Series) -> float:
        raise NotImplementedError

    @abstractmethod
    def align_request(
        self, factor_id: str, mechanism: str, evidence: dict[str, Any]
    ) -> AlignRequest:
        raise NotImplementedError


def gate_record_complete(rec: GateRecord, spec: list[GateDef]) -> bool:
    return rec.is_complete(spec)


__all__ = [
    "AlignRequest",
    "DomainData",
    "FeatureSpace",
    "GateDef",
    "ResearchDomain",
    "Threshold",
    "gate_record_complete",
]
