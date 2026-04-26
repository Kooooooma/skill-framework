#!/usr/bin/env python3
"""Validate a skill-framework skill using deterministic JSON AST checks."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from schema_validation import validate_schema_document


FRAMEWORK_REQUIRED = [
    "SKILL.md",
    "framework/philosophy.md",
    "framework/ontology.yaml",
    "framework/skill-machine.schema.json",
    "framework/node-graph.schema.json",
    "framework/node-contract.schema.json",
    "framework/rule-contract.schema.json",
    "framework/artifact-contract.schema.json",
    "framework/context-policy.schema.json",
    "framework/eval-contract.schema.json",
    "framework/node-result-contract.schema.json",
    "framework/runtime-state-contract.schema.json",
    "framework/runtime-event-contract.schema.json",
    "framework/runtime-state.schema.json",
    "framework/runtime-event.schema.json",
    "evals/pressure-scenarios.md",
    "evals/framework-pressure-scenarios.md",
    "evals/expected-behaviors.json",
    "scaffolds/canonical-skill/SKILL.md",
    "scaffolds/canonical-skill/theory.md",
    "scaffolds/canonical-skill/skill.machine.json",
    "scaffolds/canonical-skill/node.graph.json",
    "scaffolds/canonical-skill/context-policy.json",
    "scaffolds/canonical-skill/runtime.json",
    "scaffolds/canonical-skill/contracts/nodes.json",
    "scaffolds/canonical-skill/contracts/artifacts.json",
    "scaffolds/canonical-skill/contracts/node-result.json",
    "scaffolds/canonical-skill/contracts/runtime-state.json",
    "scaffolds/canonical-skill/contracts/runtime-event.json",
    "scaffolds/canonical-skill/rules/global.json",
    "scaffolds/canonical-skill/rules/state/execute.json",
    "scaffolds/canonical-skill/rules/node/main.json",
    "scaffolds/canonical-skill/rules/step/validate-and-handoff.json",
    "scaffolds/canonical-skill/evals/pressure-scenarios.md",
    "scaffolds/canonical-skill/evals/expected-behaviors.json",
    "scripts/init_skill.py",
    "scripts/validate_skill.py",
    "scripts/validate_machine.py",
    "scripts/validate_contracts.py",
    "scripts/render_skill_html.mjs",
    "scripts/render_skill_client.js",
    "scripts/run_skill_evals.py",
    "scripts/skill_runtime.py",
    "agents/metadata.json",
]

SCHEMA_ROOT = Path(__file__).resolve().parent.parent / "framework"

SPEC_SCHEMA_TARGETS = [
    ("skill-machine.schema.json", "skill.machine.json"),
    ("node-graph.schema.json", "node.graph.json"),
    ("context-policy.schema.json", "context-policy.json"),
    ("eval-contract.schema.json", "evals/expected-behaviors.json"),
    ("node-contract.schema.json", "contracts/nodes.json"),
    ("artifact-contract.schema.json", "contracts/artifacts.json"),
    ("node-result-contract.schema.json", "contracts/node-result.json"),
    ("runtime-state-contract.schema.json", "contracts/runtime-state.json"),
    ("runtime-event-contract.schema.json", "contracts/runtime-event.json"),
]

CONTRACT_SCHEMA_TARGETS = [
    ("context-policy.schema.json", "context-policy.json"),
    ("node-contract.schema.json", "contracts/nodes.json"),
    ("artifact-contract.schema.json", "contracts/artifacts.json"),
    ("node-result-contract.schema.json", "contracts/node-result.json"),
    ("runtime-state-contract.schema.json", "contracts/runtime-state.json"),
    ("runtime-event-contract.schema.json", "contracts/runtime-event.json"),
]

RULE_SCHEMA = "rule-contract.schema.json"

GENERATED_REQUIRED = [
    "SKILL.md",
    "theory.md",
    "skill.machine.json",
    "node.graph.json",
    "context-policy.json",
    "runtime.json",
    "rules/global.json",
    "rules/state/execute.json",
    "rules/node/main.json",
    "rules/step/validate-and-handoff.json",
    "contracts/nodes.json",
    "contracts/artifacts.json",
    "contracts/node-result.json",
    "contracts/runtime-state.json",
    "contracts/runtime-event.json",
    "evals/pressure-scenarios.md",
    "evals/expected-behaviors.json",
    "agents/metadata.json",
]


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_json(path: Path, report: Report) -> Any:
    try:
        return json.loads(read(path))
    except FileNotFoundError:
        report.error(f"Missing JSON file: {path}")
    except json.JSONDecodeError as exc:
        report.error(f"Invalid JSON {path}: {exc}")
    return None


def framework_schema_root(root: Path) -> Path:
    local = root / "framework"
    if local.exists():
        return local
    return SCHEMA_ROOT


def check_json_schema(root: Path, schema_name: str, target_rel: str, report: Report) -> None:
    schema_path = framework_schema_root(root) / schema_name
    target_path = root / target_rel
    schema = load_json(schema_path, report)
    target = load_json(target_path, report)
    if not isinstance(schema, dict) or target is None:
        return
    for error in validate_schema_document(target, schema):
        report.error(f"{target_rel} violates framework/{schema_name}: {error}")


def check_schema_targets(root: Path, report: Report) -> None:
    for schema_name, target_rel in SPEC_SCHEMA_TARGETS:
        check_json_schema(root, schema_name, target_rel, report)
    for path in sorted((root / "rules").rglob("*.json")):
        check_json_schema(root, RULE_SCHEMA, str(path.relative_to(root)), report)


def check_contract_schema_targets(root: Path, report: Report) -> None:
    for schema_name, target_rel in CONTRACT_SCHEMA_TARGETS:
        check_json_schema(root, schema_name, target_rel, report)
    for path in sorted((root / "rules").rglob("*.json")):
        check_json_schema(root, RULE_SCHEMA, str(path.relative_to(root)), report)


def strip_fragment(resource_path: str) -> str:
    return resource_path.split("#", 1)[0]


def is_wildcard(resource_path: str) -> bool:
    return "*" in strip_fragment(resource_path)


def resource_exists(root: Path, resource_path: str) -> bool:
    path = strip_fragment(resource_path)
    if is_wildcard(path):
        return True
    return (root / path).exists()


def check_required(root: Path, required: list[str], report: Report) -> None:
    for rel in required:
        if not (root / rel).exists():
            report.error(f"Missing required file: {rel}")


def check_frontmatter(root: Path, report: Report) -> None:
    path = root / "SKILL.md"
    if not path.exists():
        return
    text = read(path)
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        report.error("SKILL.md must start with YAML frontmatter.")
        return
    frontmatter = match.group(1)
    name = re.search(r"^name:\s*([A-Za-z0-9_-]+)\s*$", frontmatter, re.MULTILINE)
    description = re.search(r"^description:\s*(.+?)\s*$", frontmatter, re.MULTILINE)
    if not name:
        report.error("SKILL.md frontmatter must include name.")
    elif name.group(1).startswith("__") and name.group(1).endswith("__"):
        pass
    elif not re.match(r"^[a-z0-9-]+$", name.group(1)):
        report.error("SKILL.md frontmatter name must use lowercase hyphen-case.")
    elif name.group(1) != root.name:
        report.warn(f"Skill name '{name.group(1)}' differs from folder name '{root.name}'.")
    if not description:
        report.error("SKILL.md frontmatter must include description.")
    elif len(description.group(1).split()) > 80:
        report.warn("Frontmatter description is long; keep it trigger-focused.")


def check_no_legacy_runtime_yaml(root: Path, report: Report) -> None:
    for rel in ["skill.machine.yaml", "node.graph.yaml", "context-policy.yaml"]:
        if (root / rel).exists():
            report.error(f"Runtime spec must be JSON, not legacy YAML: {rel}")
    for rel in ["contracts/nodes.yaml", "contracts/artifacts.yaml", "contracts/node-result.yaml", "rules/global.yaml", "evals/expected-behaviors.yaml"]:
        if (root / rel).exists():
            report.error(f"Canonical generated skill must use JSON for runtime-executable spec: {rel}")


def check_json_syntax(root: Path, report: Report) -> None:
    for path in sorted(root.rglob("*.json")):
        load_json(path, report)


def check_generated_sections(root: Path, report: Report) -> None:
    skill = root / "SKILL.md"
    theory = root / "theory.md"
    artifacts_contract = root / "contracts" / "artifacts.json"
    artifact_doc = load_json(artifacts_contract, report) if artifacts_contract.exists() else {}
    artifacts = artifact_doc.get("artifacts", {}) if isinstance(artifact_doc, dict) else {}

    skill_sections = artifacts.get("skill_entrypoint", {}).get(
        "sections",
        ["## Core Model", "## Execution", "## Available Scripts"],
    )
    theory_sections = artifacts.get("theory", {}).get(
        "sections",
        ["## Purpose", "## Domain Model", "## Invariants", "## Failure Theory", "## Judgment Rubric"],
    )

    if skill.exists():
        text = read(skill)
        for heading in skill_sections:
            if heading not in text:
                report.error(f"SKILL.md missing section: {heading}")
    if theory.exists():
        text = read(theory)
        for heading in theory_sections:
            if heading not in text:
                report.error(f"theory.md missing section: {heading}")


def graph_nodes(graph: dict[str, Any], graph_id: str) -> dict[str, Any]:
    return graph.get("graphs", {}).get(graph_id, {}).get("nodes", {})


def topo_sort(nodes: dict[str, Any], report: Report, graph_id: str) -> list[str]:
    for node, spec in nodes.items():
        for dep in spec.get("depends_on", []):
            if dep not in nodes:
                report.error(f"Graph '{graph_id}' node '{node}' depends on unknown node '{dep}'.")
    ordered: list[str] = []
    seen: set[str] = set()
    visiting: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            report.error(f"Graph '{graph_id}' contains a cycle at node '{node}'.")
            return
        if node in seen:
            return
        visiting.add(node)
        for dep in nodes[node].get("depends_on", []):
            if dep in nodes:
                visit(dep)
        visiting.remove(node)
        seen.add(node)
        ordered.append(node)

    for node in nodes:
        visit(node)
    return ordered


def check_machine_and_graph(root: Path, report: Report) -> None:
    machine = load_json(root / "skill.machine.json", report)
    graph = load_json(root / "node.graph.json", report)
    nodes_contract = load_json(root / "contracts" / "nodes.json", report)
    runtime = load_json(root / "runtime.json", report)
    if not isinstance(machine, dict) or not isinstance(graph, dict) or not isinstance(nodes_contract, dict) or not isinstance(runtime, dict):
        return

    machine_body = machine.get("machine", {})
    states = machine_body.get("states", {})
    state_names = set(states)
    initial = machine_body.get("initial")
    terminal = set(machine_body.get("terminal", []))
    if initial not in state_names:
        report.error(f"Machine initial state does not exist: {initial}")
    for state in terminal:
        if state not in state_names:
            report.error(f"Machine terminal state does not exist: {state}")
        elif states[state].get("on"):
            report.error(f"Terminal state must not define transitions: {state}")

    available_graphs = set(graph.get("graphs", {}))
    graph_refs: dict[str, str] = {}
    for state, spec in states.items():
        graph_ref = spec.get("graph")
        if graph_ref:
            graph_refs[state] = graph_ref
            if graph_ref not in available_graphs:
                report.error(f"State '{state}' references missing graph '{graph_ref}'.")
        for event, target in spec.get("on", {}).items():
            if target not in state_names:
                report.error(f"State '{state}' transition '{event}' targets unknown state '{target}'.")

    loop_guards = runtime.get("runtime", {}).get("loop_guards", {})
    max_visits = loop_guards.get("max_state_visits", {})
    max_self = loop_guards.get("max_consecutive_self_transitions")
    for state, spec in states.items():
        for _event, target in spec.get("on", {}).items():
            if target == state and max_self is None:
                report.error(f"Self-loop transition on '{state}' requires runtime.loop_guards.max_consecutive_self_transitions.")
            if target in graph_refs and target in state_names and target not in max_visits and target != state:
                report.warn(f"Transition to non-terminal state '{target}' has no max_state_visits guard.")

    declared_contracts = nodes_contract.get("nodes", {})
    for graph_id, graph_spec in graph.get("graphs", {}).items():
        nodes = graph_spec.get("nodes", {})
        if not nodes:
            report.error(f"Graph '{graph_id}' must define at least one node.")
            continue
        topo_sort(nodes, report, graph_id)
        writes: dict[str, str] = {}
        for node, spec in nodes.items():
            contract = spec.get("contract", "")
            contract_name = contract.rsplit("/", 1)[-1] if "#/nodes/" in contract else ""
            if "#/nodes/" in contract:
                contract_name = contract.split("#/nodes/", 1)[1]
            if not contract_name or contract_name not in declared_contracts:
                report.error(f"Graph '{graph_id}' node '{node}' references missing node contract '{contract}'.")
            for written in spec.get("writes", []):
                if written in writes:
                    report.error(f"Graph '{graph_id}' write-set conflict for '{written}' between '{writes[written]}' and '{node}'.")
                writes[written] = node


def check_node_contracts(root: Path, report: Report) -> None:
    data = load_json(root / "contracts" / "nodes.json", report)
    if not isinstance(data, dict):
        return
    for node, spec in data.get("nodes", {}).items():
        if spec.get("execution") != "sequential":
            report.error(f"Node '{node}' must declare execution: sequential.")
        if spec.get("kind") == "agent" and not spec.get("instruction") and not any(step.get("action") for step in spec.get("workflow", [])):
            report.error(f"Agent node '{node}' must include instruction or workflow actions.")
        steps = spec.get("workflow", [])
        step_numbers = [step.get("step") for step in steps]
        expected = list(range(1, len(step_numbers) + 1))
        if step_numbers != expected:
            report.error(f"Node '{node}' workflow steps must be consecutive from 1; found {step_numbers}.")
        for step in steps:
            for field in ["step", "name", "action", "done_when"]:
                if field not in step:
                    report.error(f"Node '{node}' step missing {field}: {step}")


def check_rules(root: Path, report: Report) -> None:
    for rel in ["rules/global.json", "rules/state/execute.json", "rules/node/main.json", "rules/step/validate-and-handoff.json"]:
        data = load_json(root / rel, report)
        if not isinstance(data, dict):
            continue
        for rule in data.get("rules", []):
            for field in ["id", "scope", "priority", "statement"]:
                if field not in rule:
                    report.error(f"{rel} rule missing {field}: {rule}")


def iter_context_resources(policy: dict[str, Any]) -> list[dict[str, Any]]:
    body = policy.get("context_policy", {})
    resources: list[dict[str, Any]] = []
    for key in ["always_load", "never_load_unless_requested"]:
        resources.extend(body.get(key, []))
    for key in ["on_state", "on_node", "on_step", "on_failure", "on_validation"]:
        for items in body.get(key, {}).values():
            resources.extend(items)
    return resources


def check_context_policy(root: Path, report: Report) -> None:
    data = load_json(root / "context-policy.json", report)
    if not isinstance(data, dict):
        return
    body = data.get("context_policy", {})
    if body.get("forbidden_bulk_load"):
        always = body.get("always_load", [])
        if len(always) > body.get("max_context_items", 9999):
            report.error("context-policy.json always_load exceeds max_context_items.")
        bulk_paths = [item.get("path", "") for item in always if "*" in item.get("path", "")]
        if bulk_paths:
            report.error("context-policy.json forbidden_bulk_load disallows wildcard resources in always_load.")
    for resource in iter_context_resources(data):
        for field in ["path", "resource_type", "audience"]:
            if field not in resource:
                report.error(f"context-policy.json resource missing {field}: {resource}")
        path = resource.get("path", "")
        if path and not resource_exists(root, path):
            report.error(f"context-policy.json references missing resource: {path}")
        if resource.get("audience") == "runtime_only" and resource.get("resource_type") == "reference":
            report.warn(f"Reference marked runtime_only may be unintended: {path}")


def check_eval_files(root: Path, report: Report) -> None:
    data = load_json(root / "evals" / "expected-behaviors.json", report)
    pressure = root / "evals" / "pressure-scenarios.md"
    if isinstance(data, dict):
        ids = set()
        for scenario in data.get("scenarios", []):
            sid = scenario.get("id")
            if not sid:
                report.error("Eval scenario missing id.")
                continue
            ids.add(sid)
            for field in ["prompt", "expected_behavior", "forbidden_behavior", "pass_criteria"]:
                if field not in scenario:
                    report.error(f"Eval scenario '{sid}' missing {field}.")
        if pressure.exists():
            text = read(pressure)
            for sid in ids:
                if f"## {sid}" not in text:
                    report.error(f"Expected eval scenario missing pressure heading: {sid}")
        else:
            report.error("Missing evals/pressure-scenarios.md")


def validate(root: Path) -> Report:
    report = Report()
    if not root.exists():
        report.error(f"Path does not exist: {root}")
        return report
    if root.name == "skill-framework":
        check_required(root, FRAMEWORK_REQUIRED, report)
        check_json_syntax(root / "framework", report)
        check_schema_targets(root, report)
        check_generated_sections(root, report)
        check_machine_and_graph(root, report)
        check_node_contracts(root, report)
        check_rules(root, report)
        check_context_policy(root, report)
        check_eval_files(root, report)
        scaffold = root / "scaffolds" / "canonical-skill"
        if scaffold.exists():
            generated_report = validate(scaffold)
            report.errors.extend(f"scaffold: {item}" for item in generated_report.errors)
            report.warnings.extend(f"scaffold: {item}" for item in generated_report.warnings)
    else:
        check_required(root, GENERATED_REQUIRED, report)
        check_no_legacy_runtime_yaml(root, report)
        check_json_syntax(root, report)
        check_schema_targets(root, report)
        check_generated_sections(root, report)
        check_machine_and_graph(root, report)
        check_node_contracts(root, report)
        check_rules(root, report)
        check_context_policy(root, report)
        check_eval_files(root, report)
    check_frontmatter(root, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a framework-compliant skill.")
    parser.add_argument("skill_path")
    args = parser.parse_args()
    root = Path(args.skill_path).expanduser().resolve()
    report = validate(root)
    for warning in report.warnings:
        print(f"WARN: {warning}")
    for error in report.errors:
        print(f"ERROR: {error}")
    if report.errors:
        print(f"FAILED: {len(report.errors)} error(s), {len(report.warnings)} warning(s)")
        return 1
    print(f"OK: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
