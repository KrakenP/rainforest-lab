#!/usr/bin/env python3
"""Validate minimal Rainforest state files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


FOREST_REQUIRED_KEYS = ("research_goal", "domain", "climate", "trees")
SEED_BANK_REQUIRED_KEYS = ("seed_policy", "scoring_weights", "seeds")


def load_top_level_keys(path: Path) -> set[str]:
    """Return top-level keys from JSON or simple YAML files."""

    text = path.read_text(encoding="utf-8")
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return set(parsed)
    except json.JSONDecodeError:
        pass

    keys: set[str] = set()
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[:1].isspace() or ":" not in line:
            continue
        key = line.split(":", 1)[0].strip()
        if key:
            keys.add(key)
    return keys


def required_keys_for(path: Path, keys: set[str]) -> tuple[str, ...]:
    if "seeds" in keys and ("seed_policy" in keys or "scoring_weights" in keys):
        return SEED_BANK_REQUIRED_KEYS
    if path.name.lower().startswith("seed"):
        return SEED_BANK_REQUIRED_KEYS
    return FOREST_REQUIRED_KEYS


def validate_file(path: Path) -> list[str]:
    keys = load_top_level_keys(path)
    required = required_keys_for(path, keys)
    errors = []
    for key in required:
        if key not in keys:
            errors.append(f"{path}: missing required key: {key}")
    return errors


def validate_files(paths: list[Path]) -> list[str]:
    errors: list[str] = []
    for path in paths:
        errors.extend(validate_file(path))
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate Rainforest forest state and seed bank files.")
    parser.add_argument("paths", nargs="*", type=Path, help="State files to validate.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.paths:
        parser.print_help()
        return 0
    errors = validate_files(args.paths)
    if errors:
        for error in errors:
            print(error)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
