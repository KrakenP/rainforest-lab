from __future__ import annotations

import pytest

from rainforest_lab.dsl.types import OpDef, OpRegistry


def test_op_def_arity() -> None:
    op = OpDef(name="add", arity=2, kind="binary", fn=lambda a, b: a + b)
    assert op.arity == 2


def test_registry_register_and_get() -> None:
    reg = OpRegistry()
    op = OpDef(name="neg", arity=1, kind="unary", fn=lambda x: -x)
    reg.register(op)
    assert reg.get("neg") is op


def test_registry_duplicate_raises() -> None:
    reg = OpRegistry()
    op = OpDef(name="neg", arity=1, kind="unary", fn=lambda x: -x)
    reg.register(op)
    with pytest.raises(ValueError, match="already registered"):
        reg.register(op)


def test_registry_fields_separate_from_ops() -> None:
    reg = OpRegistry()
    reg.register_field("close")
    reg.register_field("volume")
    assert reg.fields == ("close", "volume")
    assert "close" not in reg.ops


def test_registry_names_immutable_tuple() -> None:
    reg = OpRegistry()
    reg.register_field("close")
    fields = reg.fields
    with pytest.raises(AttributeError):
        fields.append("hack")  # type: ignore[attr-defined]
