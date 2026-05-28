from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rainforest_lab.logging import get_logger

LOGGER = get_logger(__name__)

# Canonical agent-attributed action types for the v2.5 visualization replay source. `emit` does NOT
# enforce membership (arbitrary callers stay valid); this registry documents/discovers the known
# action vocabulary. v2.0 adds the deliberation/parallel/skeptic action types.
KNOWN_ACTIONS: frozenset[str] = frozenset(
    {
        # v1
        "validate_pre",
        "route",
        "mine",
        "judge",
        "rank_and_route_seeds",
        "nursery_check",
        "evaluate",
        "classify",
        "validate_post_save",
        "handoff_request",
        "handoff_response",
        "handoff_timeout",
        "handoff_schema_violation",
        "handoff_submit_response",
        "handoff_divergence",
        "handoff_g7_alignment",
        # v2.0
        "debate_round",
        "skeptic_challenge",
        "gardener_parallel_dispatch",
    }
)


def emit(
    agent: str,
    role: str,
    action: str,
    target: str,
    *,
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    reason: str,
    cycle: int,
    events_path: Path = Path("./logs/events.jsonl"),
) -> None:
    if not reason.strip():
        raise ValueError("reason must be non-empty")

    event = {
        "ts": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "agent": agent,
        "role": role,
        "action": action,
        "target": target,
        "inputs": inputs,
        "outputs": outputs,
        "reason": reason,
        "cycle": cycle,
        "initiative": "rainforest_lab",
    }

    events_path.parent.mkdir(parents=True, exist_ok=True)
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    LOGGER.info("rainforest_event_emitted", extra=event)


__all__ = ["KNOWN_ACTIONS", "emit"]
