import json
from pathlib import Path

import pytest

from rainforest_lab.events import emit


def test_emit_appends_jsonl(tmp_path: Path) -> None:
    events_path = tmp_path / "events.jsonl"

    emit(
        "codex",
        "engineer",
        "validate",
        "forest",
        inputs={"cycle": "cycle_001"},
        outputs={"status": "ok"},
        reason="record validation outcome",
        cycle=1,
        events_path=events_path,
    )

    lines = events_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert event["ts"].endswith("Z")
    assert event["agent"] == "codex"
    assert event["role"] == "engineer"
    assert event["action"] == "validate"
    assert event["target"] == "forest"
    assert event["inputs"] == {"cycle": "cycle_001"}
    assert event["outputs"] == {"status": "ok"}
    assert event["reason"] == "record validation outcome"
    assert event["cycle"] == 1
    assert event["initiative"] == "rainforest_lab"


def test_v2_action_types_registered() -> None:
    from rainforest_lab.events import KNOWN_ACTIONS

    assert {"debate_round", "skeptic_challenge", "gardener_parallel_dispatch"} <= KNOWN_ACTIONS


def test_emit_empty_reason_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        emit(
            "codex",
            "engineer",
            "validate",
            "forest",
            inputs={},
            outputs={},
            reason="",
            cycle=1,
            events_path=tmp_path / "events.jsonl",
        )
