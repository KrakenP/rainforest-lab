"""Rainforest Lab error hierarchy. All raise sites that the engine treats as 'hard fail' use
RainforestError or a subclass; classification + validate use ValueError for type/contract
violations the way pydantic itself does."""

from __future__ import annotations

from typing import Any


class RainforestError(Exception):
    """Base error for the rainforest engine. Carries an optional structured ``context`` dict."""

    def __init__(self, message: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.context: dict[str, Any] = dict(context or {})


__all__ = ["RainforestError"]
