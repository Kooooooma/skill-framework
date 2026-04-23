#!/usr/bin/env python3
"""Create a skill-framework/v1 skill from the canonical scaffold."""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCAFFOLD = ROOT / "scaffolds" / "canonical-skill"


def hyphen_name(value: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    name = re.sub(r"-+", "-", name)
    if not name:
        raise SystemExit("Skill name must contain at least one letter or digit.")
    if len(name) > 64:
        raise SystemExit("Skill name must be 64 characters or fewer.")
    return name


def title_from_name(name: str) -> str:
    return " ".join(part.capitalize() for part in name.split("-"))


def replace_placeholders(path: Path, replacements: dict[str, str]) -> None:
    if path.is_dir():
        return
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return
    for key, value in replacements.items():
        text = text.replace(key, value)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a skill-framework/v1 skill scaffold.")
    parser.add_argument("skill_name", help="Skill name. It will be normalized to hyphen-case.")
    parser.add_argument("--path", required=True, help="Directory that will receive the new skill folder.")
    parser.add_argument("--description", help="Trigger-only skill description.")
    parser.add_argument("--purpose", help="One-sentence theory purpose.")
    args = parser.parse_args()

    skill_name = hyphen_name(args.skill_name)
    title = title_from_name(skill_name)
    out_root = Path(args.path).expanduser().resolve()
    target = out_root / skill_name

    if target.exists():
        raise SystemExit(f"Refusing to overwrite existing skill: {target}")
    if not SCAFFOLD.exists():
        raise SystemExit(f"Missing scaffold: {SCAFFOLD}")

    description = args.description or (
        f"Use when working on {title} tasks through a framework-compliant LLM workflow program "
        "with theory, state machine, DAG node graph, sequential node steps, scoped rules, "
        "contracts, runtime context slicing, validators, and behavior evals."
    )
    purpose = args.purpose or f"Provide a framework-compliant workflow for {title} tasks."
    short_description = description.split(".")[0][:80]

    shutil.copytree(SCAFFOLD, target)
    for rel in ["references", "scripts", "rules", "rules/state", "rules/node", "rules/step", "contracts", "evals", "agents"]:
        (target / rel).mkdir(exist_ok=True)
    replacements = {
        "__SKILL_NAME__": skill_name,
        "__SKILL_TITLE__": title,
        "__SKILL_DESCRIPTION__": description,
        "__SKILL_PURPOSE__": purpose,
        "__SKILL_SHORT_DESCRIPTION__": short_description,
    }
    for path in target.rglob("*"):
        replace_placeholders(path, replacements)

    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
