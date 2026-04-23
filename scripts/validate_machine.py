#!/usr/bin/env python3
"""Validate machine and graph specs for a skill-framework skill."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_skill import Report, check_machine_and_graph  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate skill.machine.json and node.graph.json.")
    parser.add_argument("skill_path")
    args = parser.parse_args()
    root = Path(args.skill_path).expanduser().resolve()
    report = Report()
    check_machine_and_graph(root, report)
    for warning in report.warnings:
        print(f"WARN: {warning}")
    for error in report.errors:
        print(f"ERROR: {error}")
    if report.errors:
        return 1
    print(f"OK: machine and graph valid for {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
