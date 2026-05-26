#!/usr/bin/env python3
"""Score Rainforest seeds and draft a cycle plan."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


DEFAULT_WEIGHTS = {
    "novelty": 0.25,
    "logic_strength": 0.20,
    "option_value": 0.15,
    "cross_tree_potential": 0.15,
    "regime_relevance": 0.10,
    "evidence_hint": 0.10,
    "data_availability": 0.05,
    "validation_cost": -0.15,
    "leakage_risk": -0.20,
    "redundancy": -0.10,
}


def score_seed(seed: dict[str, Any], weights: dict[str, float] | None = None) -> float:
    """Return the high-potential-biased Rainforest seed score."""

    active_weights = weights or DEFAULT_WEIGHTS
    scores = seed.get("scores", {})
    total = 0.0
    for field, weight in active_weights.items():
        total += float(scores.get(field, 0.0)) * weight
    return round(total, 3)


def rank_seeds(seed_bank: dict[str, Any]) -> list[dict[str, Any]]:
    """Score, route, and sort seeds for the next sowing pass."""

    policy = seed_bank.get("seed_policy", {})
    slots = int(policy.get("seed_slots", 3))
    leakage_threshold = float(policy.get("quarantine_leakage_threshold", 0.8))
    weights = seed_bank.get("scoring_weights") or DEFAULT_WEIGHTS

    ranked: list[dict[str, Any]] = []
    for seed in seed_bank.get("seeds", []):
        routed = dict(seed)
        routed["seed_score"] = score_seed(seed, weights)
        leakage_risk = float(seed.get("scores", {}).get("leakage_risk", 0.0))
        routed["status"] = "quarantine" if leakage_risk >= leakage_threshold else "hold"
        ranked.append(routed)

    non_quarantined = sorted(
        [seed for seed in ranked if seed["status"] != "quarantine"],
        key=lambda seed: seed["seed_score"],
        reverse=True,
    )
    quarantined = sorted(
        [seed for seed in ranked if seed["status"] == "quarantine"],
        key=lambda seed: seed["seed_score"],
        reverse=True,
    )

    for seed in non_quarantined[:slots]:
        seed["status"] = "sow_now"

    return non_quarantined + quarantined


def render_cycle_plan(ranked_seeds: list[dict[str, Any]]) -> str:
    """Render a Markdown seed sowing queue."""

    lines = [
        "# Rainforest Cycle Plan",
        "",
        "## Seed Sowing Queue",
        "",
        "| Rank | Seed | Score | Routing | First Validation |",
        "|---:|---|---:|---|---|",
    ]
    for index, seed in enumerate(ranked_seeds, start=1):
        lines.append(
            "| {rank} | {seed_id} | {score:.3f} | {status} | {validation} |".format(
                rank=index,
                seed_id=seed.get("seed_id", ""),
                score=float(seed.get("seed_score", 0.0)),
                status=seed.get("status", ""),
                validation=seed.get("validation_plan", ""),
            )
        )
    return "\n".join(lines) + "\n"


def load_seed_bank(path: Path) -> dict[str, Any]:
    """Load JSON seed banks; explain YAML limitations without PyYAML."""

    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"{path}: could not parse as JSON. Install PyYAML or convert this seed bank to JSON for script use."
        ) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rank Rainforest seeds and draft a cycle plan.")
    parser.add_argument("seed_bank", nargs="?", type=Path, help="Path to a JSON seed bank.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.seed_bank is None:
        parser.print_help()
        return 0
    seed_bank = load_seed_bank(args.seed_bank)
    ranked = rank_seeds(seed_bank)
    sys.stdout.write(render_cycle_plan(ranked))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
