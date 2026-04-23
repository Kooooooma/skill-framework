#!/usr/bin/env python3
"""Validate contracts, rules, and context policy for a skill-framework skill."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_skill import (  # noqa: E402
    Report,
    check_context_policy,
    check_generated_sections,
    check_node_contracts,
    check_rules,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate node, artifact, rule, and context contracts.")
    parser.add_argument("skill_path")
    args = parser.parse_args()
    root = Path(args.skill_path).expanduser().resolve()
    report = Report()
    check_generated_sections(root, report)
    check_node_contracts(root, report)
    check_rules(root, report)
    check_context_policy(root, report)
    for warning in report.warnings:
        print(f"WARN: {warning}")
    for error in report.errors:
        print(f"ERROR: {error}")
    if report.errors:
        return 1
    print(f"OK: contracts valid for {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
