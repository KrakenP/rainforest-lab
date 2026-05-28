from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

import pytest

_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["score", "notes"],
    "properties": {
        "score": {"type": "integer", "minimum": 0, "maximum": 3},
        "notes": {"type": "string"},
    },
    "additionalProperties": False,
}


def test_request_roundtrip(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from rainforest_lab import handoff

    monkeypatch.setattr(handoff, "HANDOFF_ROOT", tmp_path / "handoff")
    result_box: dict[str, dict[str, Any]] = {}

    def requester() -> None:
        result_box["result"] = handoff.request(
            "g7_alignment",
            {"factor_id": "f1"},
            _SCHEMA,
            req_id="req-1",
            timeout_s=2,
        )

    thread = threading.Thread(target=requester)
    thread.start()

    request_path = handoff.HANDOFF_ROOT / "requests" / "req-1.json"
    deadline = time.monotonic() + 1
    while not request_path.exists() and time.monotonic() < deadline:
        time.sleep(0.01)

    assert request_path.exists()
    written = json.loads(request_path.read_text(encoding="utf-8"))
    assert written["kind"] == "g7_alignment"
    assert written["payload"] == {"factor_id": "f1"}
    assert written["response_schema"] == _SCHEMA

    handoff.submit_response("req-1", {"score": 2, "notes": "sound enough"})
    thread.join(timeout=2)

    assert not thread.is_alive()
    assert result_box["result"] == {"score": 2, "notes": "sound enough"}


def test_request_timeout_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from rainforest_lab import handoff

    monkeypatch.setattr(handoff, "HANDOFF_ROOT", tmp_path / "handoff")

    with pytest.raises(TimeoutError):
        handoff.request(
            "divergence",
            {"mechanisms": []},
            {"type": "object"},
            req_id="req-timeout",
            timeout_s=0,
        )


def test_response_schema_violation_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from rainforest_lab import handoff

    monkeypatch.setattr(handoff, "HANDOFF_ROOT", tmp_path / "handoff")

    def responder() -> None:
        response_dir = handoff.HANDOFF_ROOT / "responses"
        response_dir.mkdir(parents=True, exist_ok=True)
        time.sleep(0.05)
        (response_dir / "req-bad.json").write_text(
            json.dumps({"score": "high", "notes": "bad type"}),
            encoding="utf-8",
        )

    thread = threading.Thread(target=responder)
    thread.start()

    with pytest.raises(ValueError, match="schema"):
        handoff.request(
            "g7_alignment",
            {"factor_id": "f1"},
            _SCHEMA,
            req_id="req-bad",
            timeout_s=2,
        )
    thread.join(timeout=2)


def test_open_requests_lists_pending(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from rainforest_lab import handoff

    monkeypatch.setattr(handoff, "HANDOFF_ROOT", tmp_path / "handoff")
    request_dir = handoff.HANDOFF_ROOT / "requests"
    response_dir = handoff.HANDOFF_ROOT / "responses"
    request_dir.mkdir(parents=True)
    response_dir.mkdir(parents=True)

    (request_dir / "pending.json").write_text(
        json.dumps(
            {
                "kind": "divergence",
                "payload": {"x": 1},
                "response_schema": {"type": "object"},
            }
        ),
        encoding="utf-8",
    )
    (request_dir / "answered.json").write_text(
        json.dumps(
            {
                "kind": "g7_alignment",
                "payload": {"x": 2},
                "response_schema": {"type": "object"},
            }
        ),
        encoding="utf-8",
    )
    (response_dir / "answered.json").write_text(json.dumps({}), encoding="utf-8")

    assert handoff.open_requests() == [
        {
            "req_id": "pending",
            "kind": "divergence",
            "payload": {"x": 1},
            "response_schema": {"type": "object"},
        }
    ]


def test_handoff_root_argument_overrides_module_default(tmp_path: Path) -> None:
    """The new optional ``root`` arg lets callers redirect without monkeypatching."""
    from rainforest_lab import handoff

    custom = tmp_path / "custom_handoff"
    response_dir = custom / "responses"
    response_dir.mkdir(parents=True)
    (response_dir / "req-arg.json").write_text(
        json.dumps({"score": 1, "notes": "ok"}), encoding="utf-8"
    )

    out = handoff.request(
        "g7_alignment",
        {"factor_id": "f1"},
        _SCHEMA,
        req_id="req-arg",
        timeout_s=2,
        root=custom,
    )
    assert out == {"score": 1, "notes": "ok"}
