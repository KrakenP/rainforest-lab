from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Literal

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

from rainforest_lab.events import emit
from rainforest_lab.logging import get_logger

HANDOFF_ROOT = Path("./runs/handoff")
POLL_INTERVAL_S = 0.05

LOGGER = get_logger(__name__)
HandoffKind = Literal["divergence", "g7_alignment"]


def request(
    kind: HandoffKind,
    payload: dict[str, Any],
    schema: dict[str, Any],
    *,
    req_id: str,
    timeout_s: int,
    root: Path | None = None,
) -> dict[str, Any]:
    if not req_id.strip():
        raise ValueError("req_id must be non-empty")
    if timeout_s < 0:
        raise ValueError("timeout_s must be non-negative")

    role = _role_for_kind(kind)
    request_dir, response_dir = _ensure_dirs(root)
    request_path = request_dir / f"{req_id}.json"
    response_path = response_dir / f"{req_id}.json"
    request_payload = {"kind": kind, "payload": payload, "response_schema": schema}

    _write_json_atomic(request_path, request_payload)
    emit(
        "Claude",
        role,
        "handoff_request",
        req_id,
        inputs={"kind": kind, "payload": payload},
        outputs={"request_path": str(request_path), "response_schema": schema},
        reason="schema-constrained handoff request written for host-mediated response.",
        cycle=0,
    )
    LOGGER.info("rainforest_handoff_request_written kind=%s req_id=%s path=%s",
                kind, req_id, request_path)

    deadline = time.monotonic() + timeout_s
    while True:
        if response_path.exists():
            response_payload = _read_json_object(response_path)
            try:
                Draft202012Validator(schema).validate(response_payload)
            except JsonSchemaValidationError as exc:
                emit(
                    "Claude",
                    role,
                    "handoff_schema_violation",
                    req_id,
                    inputs={"kind": kind, "response_path": str(response_path)},
                    outputs={"error": exc.message},
                    reason="rejected a handoff response that violated its declared schema.",
                    cycle=0,
                )
                raise ValueError(
                    f"handoff response schema violation for {req_id}: {exc.message}"
                ) from exc
            emit(
                "Claude",
                role,
                "handoff_response",
                req_id,
                inputs={"kind": kind, "response_path": str(response_path)},
                outputs=response_payload,
                reason="accepted a schema-valid host-mediated handoff response.",
                cycle=0,
            )
            return response_payload

        if time.monotonic() >= deadline:
            emit(
                "Claude",
                role,
                "handoff_timeout",
                req_id,
                inputs={"kind": kind, "timeout_s": timeout_s},
                outputs={"response_path": str(response_path)},
                reason="handoff timed out and requires hard failure.",
                cycle=0,
            )
            raise TimeoutError(f"handoff response timed out for {req_id} after {timeout_s}s")
        time.sleep(POLL_INTERVAL_S)


def open_requests(root: Path | None = None) -> list[dict[str, Any]]:
    request_dir, response_dir = _ensure_dirs(root)
    pending: list[dict[str, Any]] = []
    for path in sorted(request_dir.glob("*.json")):
        response_path = response_dir / path.name
        if response_path.exists():
            continue
        item = _read_json_object(path)
        item["req_id"] = path.stem
        pending.append(
            {
                "req_id": item["req_id"],
                "kind": item.get("kind"),
                "payload": item.get("payload"),
                "response_schema": item.get("response_schema"),
            }
        )
    return pending


def submit_response(req_id: str, payload: dict[str, Any], root: Path | None = None) -> None:
    if not req_id.strip():
        raise ValueError("req_id must be non-empty")
    request_dir, response_dir = _ensure_dirs(root)
    role = _role_from_request(request_dir / f"{req_id}.json")
    response_path = response_dir / f"{req_id}.json"
    _write_json_atomic(response_path, payload)
    emit(
        "Claude",
        role,
        "handoff_submit_response",
        req_id,
        inputs={"req_id": req_id},
        outputs=payload,
        reason="host submitted a handoff response for the engine to validate at request boundary.",
        cycle=0,
    )
    LOGGER.info("rainforest_handoff_response_submitted req_id=%s path=%s", req_id, response_path)


def _role_for_kind(kind: HandoffKind) -> str:
    return "diverger" if kind == "divergence" else "aligner"


def _role_from_request(path: Path) -> str:
    if not path.exists():
        return "aligner"
    request_payload = _read_json_object(path)
    return "diverger" if request_payload.get("kind") == "divergence" else "aligner"


def _ensure_dirs(root: Path | None) -> tuple[Path, Path]:
    base = Path(root) if root else HANDOFF_ROOT
    request_dir = base / "requests"
    response_dir = base / "responses"
    request_dir.mkdir(parents=True, exist_ok=True)
    response_dir.mkdir(parents=True, exist_ok=True)
    return request_dir, response_dir


def _read_json_object(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(path)


__all__ = ["HANDOFF_ROOT", "open_requests", "request", "submit_response"]
