#!/usr/bin/env python3
"""Validate skill eval definitions and scenario coverage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Check eval scenario definitions.")
    parser.add_argument("skill_path")
    args = parser.parse_args()
    root = Path(args.skill_path).expanduser().resolve()
    expected = root / "evals" / "expected-behaviors.json"
    pressure = root / "evals" / "pressure-scenarios.md"
    errors: list[str] = []

    if not expected.exists():
        errors.append("Missing evals/expected-behaviors.json")
    if not pressure.exists():
        errors.append("Missing evals/pressure-scenarios.md")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    try:
        data = json.loads(expected.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: Invalid eval JSON: {exc}")
        return 1
    pressure_text = pressure.read_text(encoding="utf-8")

    ids: set[str] = set()
    for scenario in data.get("scenarios", []):
        sid = scenario.get("id")
        if not sid:
            errors.append("Scenario missing id")
            continue
        ids.add(sid)
        for field in ["prompt", "expected_behavior", "forbidden_behavior", "pass_criteria"]:
            if not scenario.get(field):
                errors.append(f"Scenario '{sid}' missing {field}")
        if f"## {sid}" not in pressure_text:
            errors.append(f"Expected scenario missing pressure heading: {sid}")

    if not ids:
        errors.append("No scenarios found in expected-behaviors.json")

    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        return 1
    print(f"OK: eval definitions valid for {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
