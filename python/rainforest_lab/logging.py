"""Thin wrapper around stdlib logging. Returns a child logger under the ``rainforest_lab`` root;
logger configuration (handlers, formatters, levels) is the host application's responsibility,
matching the 12-factor 'log to stdout' convention."""

from __future__ import annotations

import logging


def get_logger(name: str) -> logging.Logger:
    """Return a stdlib logger. Idempotent — repeated calls with the same name return the same
    ``Logger`` instance (stdlib behaviour)."""
    return logging.getLogger(name)


__all__ = ["get_logger"]
