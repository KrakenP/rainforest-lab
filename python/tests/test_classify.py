import pytest

from rainforest_lab.classify import classify
from rainforest_lab.state import GateDef, GateRecord


def _spec() -> list[GateDef]:
    return [
        GateDef(name="G1", hard=True),
        GateDef(name="G2", hard=True),
        GateDef(name="G3", hard=True),
        GateDef(name="G7", hard=False, needs_handoff=True),
    ]


def _record(gates: dict[str, dict[str, object]], *, mode: str = "tool_executed") -> GateRecord:
    return GateRecord(domain="demo", factor_id="f1", gates=gates, execution_mode=mode)  # type: ignore[arg-type]


def test_stub_cannot_be_fruit_raises() -> None:
    rec = _record(
        {
            "G1": {"passed": True},
            "G2": {"passed": True},
            "G3": {"passed": True},
            "G7": {"score": 1, "response": "ensemble ok"},
        },
        mode="stub_result",
    )

    with pytest.raises(ValueError, match="fruit requires execution_mode"):
        classify(rec, _spec())


def test_complete_all_hard_g7_2_is_fruit_promoted() -> None:
    rec = _record(
        {
            "G1": {"passed": True},
            "G2": {"passed": True},
            "G3": {"passed": True},
            "G7": {"score": 2, "response": "promote"},
        }
    )

    label, reason = classify(rec, _spec())

    assert label == "fruit"
    assert "promoted" in reason


def test_g7_1_is_fruit_ensemble() -> None:
    rec = _record(
        {
            "G1": {"passed": True},
            "G2": {"passed": True},
            "G3": {"passed": True},
            "G7": {"score": 1, "response": "ensemble ok"},
        }
    )

    label, reason = classify(rec, _spec())

    assert label == "fruit"
    assert "ensemble" in reason


def test_hard_fail_is_golden() -> None:
    rec = _record(
        {
            "G1": {"passed": True},
            "G2": {"passed": False, "boundary_informative": True},
            "G3": {"passed": True},
            "G7": {"score": 0, "response": "not enough"},
        }
    )

    label, reason = classify(rec, _spec())

    assert label == "golden_leaf"
    assert "boundary" in reason


def test_lookahead_is_sick() -> None:
    rec = _record(
        {
            "G1": {"passed": True},
            "G2": {"passed": True, "lookahead": True},
            "G3": {"passed": True},
            "G7": {"score": 0, "response": "invalid"},
        }
    )

    label, reason = classify(rec, _spec())

    assert label == "sick_leaf"
    assert "blocked_from_reuse" in reason
