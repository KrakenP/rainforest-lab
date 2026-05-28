from __future__ import annotations

import logging

import pytest

from rainforest_lab.errors import RainforestError
from rainforest_lab.logging import get_logger


def test_rainforest_error_carries_context() -> None:
    err = RainforestError("bad gate", context={"factor_id": "x"})
    assert "bad gate" in str(err)
    assert err.context == {"factor_id": "x"}


def test_get_logger_returns_logger_with_module_name() -> None:
    log = get_logger("rainforest_lab.test")
    assert isinstance(log, logging.Logger)
    assert log.name == "rainforest_lab.test"


def test_get_logger_is_idempotent() -> None:
    a = get_logger("rainforest_lab.foo")
    b = get_logger("rainforest_lab.foo")
    assert a is b


def test_rainforest_error_subclassing() -> None:
    class GateError(RainforestError):
        pass

    with pytest.raises(RainforestError):
        raise GateError("gate failed", context={"gate": "g1"})
