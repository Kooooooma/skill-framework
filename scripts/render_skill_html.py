#!/usr/bin/env python3
"""Render a whole skill flow as a standalone HTML page."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import textwrap
from collections import deque
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_skill import Report, check_machine_and_graph, load_json


DEFAULT_THEME = {
    "background": "#FAFAFA",
    "foreground": "#1C1B1F",
    "muted": "#F3EDF7",
    "muted_foreground": "#49454F",
    "border_strong": "#79747E",
    "accent": "#6750A4",
    "accent_secondary": "#7D5260",
    "accent_foreground": "#FFFFFF",
    "border": "#79747E",
    "card": "#F3EDF7",
    "ring": "#6750A4",
    "error": "#B3261E",
}

STEP_ACTION_WRAP = 44
STATE_RING_RADIUS = 320
HORIZONTAL_STATE_TO_EXEC_GAP = 320
VERTICAL_STATE_TO_EXEC_GAP = 320
HORIZONTAL_EXEC_LAYER_GAP = 500
VERTICAL_EXEC_LAYER_GAP = 250
HORIZONTAL_EXEC_SIBLING_GAP = 560
VERTICAL_EXEC_SIBLING_GAP = 280
HORIZONTAL_STEP_GAP = 344
VERTICAL_STEP_GAP = 172
HORIZONTAL_STEP_START_GAP = 352
VERTICAL_STEP_START_GAP = 176


def state_levels(initial: str | None, states: dict[str, Any], terminal: set[str]) -> dict[str, int]:
    levels: dict[str, int] = {}
    if initial and initial in states:
        queue: deque[tuple[str, int]] = deque([(initial, 0)])
        while queue:
            state_name, level = queue.popleft()
            previous = levels.get(state_name)
            if previous is not None and previous <= level:
                continue
            levels[state_name] = level
            for target in states[state_name].get("on", {}).values():
                if target == state_name:
                    continue
                if target in states:
                    queue.append((target, level + 1))

    regular_max = max(levels.values()) if levels else 0
    terminal_level = regular_max + 1
    for state_name in states:
        if state_name in terminal or state_name == "blocked":
            levels[state_name] = terminal_level

    next_level = terminal_level + 1
    for state_name in states:
        if state_name not in levels:
            levels[state_name] = next_level
            next_level += 1
    return levels


def compact_label(text: str) -> str:
    return " ".join(str(text).split())


def skill_summary(root: Path, machine: dict[str, Any]) -> str:
    skill_path = root / "SKILL.md"
    if skill_path.exists():
        text = skill_path.read_text(encoding="utf-8")
        description = re.search(r"^description:\s*(.+)$", text, re.MULTILINE)
        if description:
            return compact_label(description.group(1).strip().strip('"').strip("'"))
    theory_path = root / "theory.md"
    if theory_path.exists():
        text = theory_path.read_text(encoding="utf-8")
        purpose = re.search(r"## Purpose\s+(.+?)(?:\n## |\Z)", text, re.DOTALL)
        if purpose:
            return compact_label(purpose.group(1))
    route_state = machine.get("states", {}).get("route_request", {})
    return compact_label(route_state.get("purpose", "Select a state, execution node, step, or edge to inspect its logic."))


def load_theme(root: Path) -> dict[str, str]:
    theme = dict(DEFAULT_THEME)
    design_path = root / "DESIGN.md"
    if not design_path.exists():
        return theme

    text = design_path.read_text(encoding="utf-8")
    table_tokens: dict[str, str] = {}
    for match in re.finditer(r"\|\s*`([^`]+)`\s*\|\s*`(#[0-9a-fA-F]{6})`\s*\|", text):
        table_tokens[match.group(1).strip()] = match.group(2)

    mapping = {
        "background": "background",
        "foreground": "foreground",
        "muted": "muted",
        "muted-foreground": "muted_foreground",
        "accent": "accent",
        "accent-secondary": "accent_secondary",
        "accent-foreground": "accent_foreground",
        "border": "border",
        "card": "card",
        "ring": "ring",
    }
    for token_name, theme_key in mapping.items():
        if token_name in table_tokens:
            theme[theme_key] = table_tokens[token_name]

    prose_patterns = {
        "background": r"\*\*Background\s*\(Surface\)\*\*:\s*`(#[0-9a-fA-F]{6})`",
        "foreground": r"\*\*Foreground\s*\(On Surface\)\*\*:\s*`(#[0-9a-fA-F]{6})`",
        "accent": r"\*\*Primary\*\*:\s*`(#[0-9a-fA-F]{6})`",
        "accent_foreground": r"\*\*On Primary\*\*:\s*`(#[0-9a-fA-F]{6})`",
        "muted": r"\*\*Surface Container\*\*:\s*`(#[0-9a-fA-F]{6})`",
        "card": r"\*\*Surface Container\*\*:\s*`(#[0-9a-fA-F]{6})`",
        "border": r"\*\*Outline\s*\(Border\)\*\*:\s*`(#[0-9a-fA-F]{6})`",
        "border_strong": r"\*\*Outline\s*\(Border\)\*\*:\s*`(#[0-9a-fA-F]{6})`",
        "muted_foreground": r"\*\*On Surface Variant\*\*:\s*`(#[0-9a-fA-F]{6})`",
        "accent_secondary": r"\*\*Tertiary\*\*:\s*`(#[0-9a-fA-F]{6})`",
    }
    for key, pattern in prose_patterns.items():
        match = re.search(pattern, text)
        if match:
            theme[key] = match.group(1)

    fallback_patterns = {
        "background": r"\*\*\s*Background\s*\*\*:\s*`(#[0-9a-fA-F]{6})`",
        "foreground": r"\*\*\s*Foreground\s*\*\*:\s*`(#[0-9a-fA-F]{6})`",
        "accent": r"`accent`\s*:\s*`(#[0-9a-fA-F]{6})`",
        "accent_secondary": r"`accent-secondary`\s*:\s*`(#[0-9a-fA-F]{6})`",
        "border": r"`border`\s*:\s*`(#[0-9a-fA-F]{6})`",
        "error": r"`error`\s*:\s*`(#[0-9a-fA-F]{6})`",
    }
    for key, pattern in fallback_patterns.items():
        match = re.search(pattern, text)
        if match:
            theme[key] = match.group(1)

    if theme["card"] == theme["background"]:
        theme["card"] = theme["muted"]
    if theme["ring"] == DEFAULT_THEME["ring"]:
        theme["ring"] = theme["accent"]
    return theme


def step_lines(step: dict[str, Any]) -> list[str]:
    step_no = step.get("step", "?")
    step_name = str(step.get("name", "")).strip() or f"step_{step_no}"
    action = compact_label(step.get("action", ""))
    lines = [f"{step_no}. {step_name}"]
    if action:
        lines.extend(textwrap.wrap(action, width=STEP_ACTION_WRAP, break_long_words=False, break_on_hyphens=False))
    return lines


def detail_body(parts: list[str]) -> str:
    return "\n\n".join(part for part in parts if part)


def ordered_state_names(initial: str | None, states: dict[str, Any], terminal: set[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()

    def add(state_name: str) -> None:
        if state_name in states and state_name not in seen:
            seen.add(state_name)
            ordered.append(state_name)

    if initial and initial in states:
        queue: deque[str] = deque([initial])
        while queue:
            state_name = queue.popleft()
            if state_name in seen:
                continue
            add(state_name)
            for target in states[state_name].get("on", {}).values():
                if target in states and target not in seen:
                    queue.append(target)

    regular_states = [name for name in states if name not in terminal and name != "blocked"]
    for state_name in regular_states:
        add(state_name)

    if "blocked" in states:
        add("blocked")

    for state_name in states:
        if state_name in terminal:
            add(state_name)

    for state_name in states:
        add(state_name)

    return ordered


def topo_order(nodes: dict[str, Any]) -> list[str]:
    remaining = {name: set(spec.get("depends_on", [])) for name, spec in nodes.items()}
    ready = sorted(name for name, deps in remaining.items() if not deps)
    ordered: list[str] = []

    while ready:
        node_name = ready.pop(0)
        ordered.append(node_name)
        for other_name, deps in remaining.items():
            if node_name in deps:
                deps.remove(node_name)
                if not deps and other_name not in ordered and other_name not in ready:
                    ready.append(other_name)
        ready.sort()

    for node_name in nodes:
        if node_name not in ordered:
            ordered.append(node_name)
    return ordered


def node_depths(nodes: dict[str, Any], ordered: list[str]) -> dict[str, int]:
    depths: dict[str, int] = {}
    for node_name in ordered:
        deps = [depths.get(dep, 0) for dep in nodes.get(node_name, {}).get("depends_on", [])]
        depths[node_name] = (max(deps) + 1) if deps else 0
    return depths


def transition_bend(source: tuple[float, float], target: tuple[float, float], ring_radius: float) -> float:
    dx = target[0] - source[0]
    dy = target[1] - source[1]
    chord = math.hypot(dx, dy)
    if chord == 0:
        return 0.0
    midpoint = ((source[0] + target[0]) / 2.0, (source[1] + target[1]) / 2.0)
    left_normal = (-dy / chord, dx / chord)
    toward_center = (-midpoint[0], -midpoint[1])
    sign = 1.0 if (left_normal[0] * toward_center[0] + left_normal[1] * toward_center[1]) >= 0 else -1.0
    magnitude = min(ring_radius * 0.72, max(200.0, chord * 0.92))
    return round(sign * magnitude, 2)


def library_candidates(script_path: Path, relpath: str) -> Path:
    search_roots = []
    for base in [Path.cwd().resolve(), script_path.resolve()]:
        search_roots.extend([base, *base.parents])
    seen: set[Path] = set()
    for root in search_roots:
        if root in seen:
            continue
        seen.add(root)
        candidate = root / relpath
        if candidate.exists():
            return candidate
    raise SystemExit(
        "\n".join(
            [
                f"Missing required browser dependency: {relpath}",
                "The HTML renderer requires these npm packages in a reachable node_modules tree:",
                "- cytoscape",
                "- cytoscape-elk",
                "- elkjs",
                "Install them from the repository root with:",
                "npm install",
            ]
        )
    )


def inline_script(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("</script>", "<\\/script>")


def build_payload(root: Path) -> dict[str, Any]:
    report = Report()
    check_machine_and_graph(root, report)
    if report.errors:
        raise SystemExit("\n".join(f"ERROR: {error}" for error in report.errors))

    machine_doc = load_json(root / "skill.machine.json", report)
    graph_doc = load_json(root / "node.graph.json", report)
    contracts_doc = load_json(root / "contracts" / "nodes.json", report)
    if not isinstance(machine_doc, dict) or not isinstance(graph_doc, dict) or not isinstance(contracts_doc, dict):
        raise SystemExit("ERROR: failed to load machine, graph, or node contracts.")

    machine = machine_doc.get("machine", {})
    states = machine.get("states", {})
    graphs = graph_doc.get("graphs", {})
    node_contracts = contracts_doc.get("nodes", {})
    initial = machine.get("initial")
    terminal = set(machine.get("terminal", []))
    theme = load_theme(root)
    ordered_states = ordered_state_names(initial, states, terminal)
    ring_radius = max(STATE_RING_RADIUS, 120 * len(ordered_states))
    summary = skill_summary(root, machine)

    elements: list[dict[str, Any]] = []
    edge_counter = 0
    state_positions: dict[str, tuple[float, float]] = {}

    for index, state_name in enumerate(ordered_states):
        spec = states[state_name]
        angle = (-math.pi / 2.0) + ((2.0 * math.pi * index) / max(len(ordered_states), 1))
        state_x = ring_radius * math.cos(angle)
        state_y = ring_radius * math.sin(angle)
        state_positions[state_name] = (state_x, state_y)
        state_id = f"state::{state_name}"
        state_classes = ["state"]
        if state_name == initial:
            state_classes.append("initial")
        if state_name in terminal:
            state_classes.append("terminal")
        if state_name == "blocked":
            state_classes.append("blocked")
        elements.append(
            {
                "data": {
                    "id": state_id,
                    "label": state_name,
                    "kind": "state",
                    "detail_title": state_name,
                    "detail_type": "State",
                    "detail_body": spec.get("purpose", ""),
                },
                "position": {"x": state_x, "y": state_y},
                "classes": " ".join(state_classes),
            }
        )

        graph_id = spec.get("graph")
        if not graph_id:
            continue
        graph_nodes = graphs.get(graph_id, {}).get("nodes", {})
        ordered_nodes = topo_order(graph_nodes)
        depths = node_depths(graph_nodes, ordered_nodes)
        layers: dict[int, list[str]] = {}
        for node_name in ordered_nodes:
            layers.setdefault(depths[node_name], []).append(node_name)

        radial_x = math.cos(angle)
        radial_y = math.sin(angle)
        horizontal_layout = abs(radial_x) >= abs(radial_y)
        if horizontal_layout:
            primary_x = 1.0 if radial_x >= 0 else -1.0
            primary_y = 0.0
            secondary_x = 0.0
            secondary_y = 1.0
            state_to_exec_gap = HORIZONTAL_STATE_TO_EXEC_GAP
            exec_layer_gap = HORIZONTAL_EXEC_LAYER_GAP
            exec_sibling_gap = HORIZONTAL_EXEC_SIBLING_GAP
            step_gap = HORIZONTAL_STEP_GAP
            step_start_gap = HORIZONTAL_STEP_START_GAP
        else:
            primary_x = 0.0
            primary_y = 1.0 if radial_y >= 0 else -1.0
            secondary_x = 1.0
            secondary_y = 0.0
            state_to_exec_gap = VERTICAL_STATE_TO_EXEC_GAP
            exec_layer_gap = VERTICAL_EXEC_LAYER_GAP
            exec_sibling_gap = VERTICAL_EXEC_SIBLING_GAP
            step_gap = VERTICAL_STEP_GAP
            step_start_gap = VERTICAL_STEP_START_GAP
        exec_positions: dict[str, tuple[float, float]] = {}
        root_nodes: set[str] = set()

        for depth, layer_nodes in sorted(layers.items()):
            layer_center = (len(layer_nodes) - 1) / 2.0
            for layer_index, node_name in enumerate(layer_nodes):
                tangent_shift = (layer_index - layer_center) * exec_sibling_gap
                exec_x = state_x + primary_x * (state_to_exec_gap + depth * exec_layer_gap) + secondary_x * tangent_shift
                exec_y = state_y + primary_y * (state_to_exec_gap + depth * exec_layer_gap) + secondary_y * tangent_shift
                exec_positions[node_name] = (exec_x, exec_y)
                if not graph_nodes.get(node_name, {}).get("depends_on"):
                    root_nodes.add(node_name)

        for node_name in ordered_nodes:
            exec_id = f"exec::{state_name}::{node_name}"
            contract = node_contracts.get(node_name, {})
            exec_x, exec_y = exec_positions[node_name]
            elements.append(
                {
                    "data": {
                        "id": exec_id,
                        "label": node_name,
                        "kind": "execution",
                        "detail_title": node_name,
                        "detail_type": "Execution Node",
                        "detail_body": detail_body(
                            [
                                contract.get("purpose", ""),
                                contract.get("instruction", ""),
                            ]
                        ),
                        "width": 240,
                        "height": 82,
                        "text_width": 184,
                    },
                    "position": {"x": exec_x, "y": exec_y},
                    "classes": "execution",
                }
            )

            workflow = contract.get("workflow", [])
            previous_step_id = None
            for step_index, step in enumerate(workflow):
                step_id = f"step::{state_name}::{node_name}::{step.get('step', 0)}"
                lines = step_lines(step)
                step_parts = [compact_label(step.get("action", ""))]
                if step.get("done_when"):
                    step_parts.append(f"Done when: {compact_label(step.get('done_when'))}")
                if step.get("stop_if"):
                    step_parts.append(f"Stop if: {compact_label(step.get('stop_if'))}")
                step_x = exec_x + primary_x * (step_start_gap + step_index * step_gap)
                step_y = exec_y + primary_y * (step_start_gap + step_index * step_gap)
                step_height = max(84, 28 + len(lines) * 18)
                elements.append(
                    {
                        "data": {
                            "id": step_id,
                            "label": "\n".join(lines),
                            "kind": "step",
                            "detail_title": lines[0],
                            "detail_type": "Workflow Step",
                            "detail_body": detail_body(step_parts),
                            "order": step.get("step", 0),
                            "width": 248,
                            "height": step_height,
                            "text_width": 190,
                        },
                        "position": {"x": step_x, "y": step_y},
                        "classes": "step",
                    }
                )

                edge_counter += 1
                source_id = exec_id if previous_step_id is None else previous_step_id
                elements.append(
                    {
                        "data": {
                            "id": f"edge::{edge_counter}",
                            "source": source_id,
                            "target": step_id,
                            "kind": "workflow",
                            "detail_title": "Workflow edge",
                            "detail_type": "Workflow",
                            "detail_body": f"{source_id} -> {step_id}",
                        },
                        "classes": "workflow",
                    }
                )
                previous_step_id = step_id

        for node_name in root_nodes:
            edge_counter += 1
            elements.append(
                {
                    "data": {
                        "id": f"edge::{edge_counter}",
                        "source": state_id,
                        "target": f"exec::{state_name}::{node_name}",
                        "kind": "attachment",
                        "detail_title": "State attachment",
                        "detail_type": "Attachment",
                        "detail_body": f"{state_name} -> {node_name}",
                    },
                    "classes": "attachment",
                }
            )

        for node_name, node_spec in graph_nodes.items():
            for dep in node_spec.get("depends_on", []):
                edge_counter += 1
                elements.append(
                    {
                        "data": {
                            "id": f"edge::{edge_counter}",
                            "source": f"exec::{state_name}::{dep}",
                            "target": f"exec::{state_name}::{node_name}",
                            "kind": "dependency",
                            "detail_title": "Dependency edge",
                            "detail_type": "Dependency",
                            "detail_body": f"{dep} -> {node_name}",
                        },
                        "classes": "dependency",
                    }
                )

    for state_name, spec in states.items():
        for event_name, target in spec.get("on", {}).items():
            edge_counter += 1
            edge_classes = ["transition"]
            if target == "blocked":
                edge_classes.append("to-blocked")
            elif target in terminal:
                edge_classes.append("to-terminal")
            elif target == state_name:
                edge_classes.append("self-loop")
            source_position = state_positions.get(state_name, (0.0, 0.0))
            target_position = state_positions.get(target, (0.0, 0.0))
            elements.append(
                {
                    "data": {
                        "id": f"edge::{edge_counter}",
                        "source": f"state::{state_name}",
                        "target": f"state::{target}",
                        "label": event_name,
                        "kind": "transition",
                        "detail_title": event_name,
                        "detail_type": "State Transition",
                        "detail_body": f"{state_name} -> {target}",
                        "bend_distance": 0.0 if target == state_name else transition_bend(source_position, target_position, ring_radius),
                    },
                    "classes": " ".join(edge_classes),
                }
            )

    return {
        "skill_name": root.name,
        "skill_summary": summary,
        "theme": theme,
        "elements": elements,
        "layout": {
            "ring_radius": ring_radius,
        },
    }


def html_document(payload: dict[str, Any], script_root: Path) -> str:
    theme = payload["theme"]
    cytoscape_js = inline_script(library_candidates(script_root, "node_modules/cytoscape/dist/cytoscape.min.js"))
    elk_js = inline_script(library_candidates(script_root, "node_modules/elkjs/lib/elk.bundled.js"))
    cytoscape_elk_js = inline_script(library_candidates(script_root, "node_modules/cytoscape-elk/dist/cytoscape-elk.js"))
    payload_json = json.dumps(payload, ensure_ascii=False)
    title = f"{payload['skill_name']} Flow Diagram"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    :root {{
      --bg: {theme["background"]};
      --fg: {theme["foreground"]};
      --muted: {theme["muted"]};
      --muted-fg: {theme["muted_foreground"]};
      --border: {theme["border"]};
      --border-strong: {theme["border_strong"]};
      --accent: {theme["accent"]};
      --accent-secondary: {theme["accent_secondary"]};
      --accent-fg: {theme["accent_foreground"]};
      --card: {theme["card"]};
      --ring: {theme["ring"]};
      --error: {theme["error"]};
    }}
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; height: 100%; background: var(--bg); color: var(--fg); font-family: JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, monospace; }}
    body {{ min-height: 100vh; }}
    .shell {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 0px;
      height: 100vh;
      gap: 16px;
      padding: 16px;
      transition: grid-template-columns 220ms ease;
    }}
    body.panel-open .shell {{
      grid-template-columns: minmax(0, 1fr) 360px;
    }}
    .graph-stage {{
      position: relative;
      min-width: 0;
      overflow: hidden;
    }}
    .graph-overlay {{
      position: absolute;
      top: 16px;
      right: 16px;
      z-index: 20;
      display: flex;
      align-items: flex-start;
      justify-content: flex-end;
      pointer-events: none;
    }}
    .overlay-actions {{
      pointer-events: auto;
      background: color-mix(in srgb, var(--card) 86%, transparent);
      backdrop-filter: blur(18px);
      border: 2px solid var(--border-strong);
      border-radius: 999px;
      box-shadow: 0 16px 40px rgba(28, 27, 31, 0.08);
    }}
    .overlay-actions {{
      display: flex;
      align-items: center;
      padding: 8px;
    }}
    .controls {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }}
    button {{
      appearance: none;
      border: 2px solid var(--border-strong);
      background: var(--card);
      color: var(--fg);
      border-radius: 999px;
      padding: 10px 14px;
      font: inherit;
      font-size: 11px;
      cursor: pointer;
      transition: transform 140ms ease, background 140ms ease, border-color 140ms ease;
    }}
    button:hover {{ transform: translateY(-1px); border-color: var(--accent); }}
    button.primary {{ background: linear-gradient(135deg, var(--accent), var(--accent-secondary)); color: var(--accent-fg); border-color: var(--accent); }}
    button.ghost {{ background: color-mix(in srgb, var(--card) 86%, transparent); }}
    #toggle-sidebar-btn {{
      min-width: 42px;
      padding: 10px 12px;
      font-size: 14px;
      line-height: 1;
    }}
    .panel {{
      background: var(--card);
      border: 2px solid var(--border-strong);
      border-radius: 28px;
      box-shadow: 0 16px 40px rgba(28, 27, 31, 0.08);
      overflow: hidden;
    }}
    #cy {{
      width: 100%;
      height: 100%;
      min-height: calc(100vh - 32px);
      background:
        radial-gradient(circle at top right, color-mix(in srgb, var(--accent) 10%, transparent), transparent 38%),
        radial-gradient(circle at bottom left, color-mix(in srgb, var(--accent-secondary) 14%, transparent), transparent 34%),
        var(--bg);
    }}
    .sidebar {{
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
      min-height: 0;
      width: 0;
      opacity: 0;
      pointer-events: none;
      transform: translateX(12px);
      transition: opacity 180ms ease, transform 180ms ease;
    }}
    body.panel-open .sidebar {{
      width: auto;
      opacity: 1;
      pointer-events: auto;
      transform: translateX(0);
    }}
    .sidebar-scroll {{
      min-height: 0;
      overflow: auto;
    }}
    .sidebar-section {{
      padding: 18px 18px 14px;
      border-bottom: 1px solid var(--border);
    }}
    .sidebar-section:last-child {{ border-bottom: 0; }}
    .sidebar h2 {{
      margin: 0 0 8px;
      font-size: 13px;
      color: var(--muted-fg);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .legend {{
      display: grid;
      gap: 10px;
      font-size: 12px;
    }}
    .legend-item {{
      display: grid;
      grid-template-columns: 18px minmax(0, 1fr);
      gap: 10px;
      align-items: center;
    }}
    .swatch {{
      width: 18px;
      height: 18px;
      border-radius: 999px;
      border: 2px solid var(--border-strong);
      background: var(--card);
    }}
    .swatch.execution {{ background: var(--muted); border-color: var(--accent); }}
    .swatch.step {{ border-radius: 10px; border-color: var(--border-strong); }}
    .swatch.terminal {{ background: var(--accent); border-color: var(--accent); }}
    .swatch.blocked {{ border-color: var(--error); }}
    .details {{
      display: flex;
      flex-direction: column;
      gap: 10px;
      min-height: 0;
    }}
    .details-type {{
      color: var(--muted-fg);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .details-title {{
      margin: 0;
      font-size: 18px;
      line-height: 1.3;
    }}
    .details-body {{
      white-space: pre-wrap;
      font-size: 12px;
      line-height: 1.7;
      color: var(--fg);
    }}
    .tip {{
      margin-top: 10px;
      padding: 12px 14px;
      border-radius: 16px;
      border: 2px solid color-mix(in srgb, var(--accent) 42%, var(--border-strong));
      background: color-mix(in srgb, var(--accent) 10%, var(--card));
      color: var(--fg);
      font-size: 12px;
      line-height: 1.6;
    }}
    .tip strong {{
      color: var(--accent);
    }}
    @media (max-width: 1100px) {{
      .shell {{
        grid-template-columns: 1fr;
      }}
      body.panel-open .shell {{
        grid-template-columns: 1fr;
      }}
      .sidebar {{
        position: fixed;
        top: 16px;
        right: 16px;
        bottom: 16px;
        width: min(360px, calc(100vw - 32px));
        z-index: 40;
      }}
      body:not(.panel-open) .sidebar {{
        width: min(360px, calc(100vw - 32px));
      }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <section id="graph-panel" class="graph-stage panel">
      <div class="graph-overlay">
        <div class="overlay-actions">
          <button id="toggle-sidebar-btn" class="primary" aria-label="Toggle side panel" title="Toggle side panel">☰</button>
        </div>
      </div>
      <div id="cy"></div>
    </section>
    <aside class="sidebar panel">
      <div class="sidebar-scroll">
        <div class="sidebar-section">
          <div class="controls">
            <button id="fit-btn" class="primary">Fit View</button>
            <button id="reset-btn">Reset Zoom</button>
            <button id="center-btn">Center</button>
          </div>
        </div>
        <div class="sidebar-section details">
          <h2>Details</h2>
          <div id="details-type" class="details-type">Overview</div>
          <h3 id="details-title" class="details-title">{payload["skill_name"]}</h3>
          <div id="details-body" class="details-body">{payload["skill_summary"]}</div>
          <div class="tip"><strong>Tip:</strong> click any state, edge, execution node, or workflow step to inspect the specific logic behind it.</div>
        </div>
      </div>
    </aside>
  </div>
  <script>{cytoscape_js}</script>
  <script>{elk_js}</script>
  <script>{cytoscape_elk_js}</script>
  <script>
    const payload = {payload_json};
    if (window.cytoscape && window.cytoscapeElk) {{
      window.cytoscape.use(window.cytoscapeElk);
    }}

    const detailsType = document.getElementById('details-type');
    const detailsTitle = document.getElementById('details-title');
    const detailsBody = document.getElementById('details-body');
    const body = document.body;
    const toggleSidebarBtn = document.getElementById('toggle-sidebar-btn');

    const updateDetails = (item) => {{
      if (!item) {{
        detailsType.textContent = 'Overview';
        detailsTitle.textContent = payload.skill_name;
        detailsBody.textContent = payload.skill_summary;
        return;
      }}
      const data = item.data();
      detailsType.textContent = data.detail_type || data.kind || 'Item';
      detailsTitle.textContent = data.detail_title || data.label || data.id;
      detailsBody.textContent = data.detail_body || 'No additional details available.';
    }};

    const cy = cytoscape({{
      container: document.getElementById('cy'),
      elements: payload.elements,
      wheelSensitivity: 3,
      boxSelectionEnabled: false,
      autoungrabify: false,
      minZoom: 0.18,
      maxZoom: 2.8,
      style: [
        {{
          selector: 'node',
          style: {{
            'font-family': 'JetBrains Mono, ui-monospace, monospace',
            'font-size': 11,
            'text-wrap': 'wrap',
            'text-max-width': 220,
            'text-valign': 'center',
            'text-halign': 'center',
            'color': payload.theme.foreground
          }}
        }},
        {{
          selector: 'node.state',
          style: {{
            'shape': 'ellipse',
            'background-color': payload.theme.card,
            'background-opacity': 0.96,
            'border-color': payload.theme.border_strong,
            'border-width': 3,
            'width': 124,
            'height': 124,
            'padding': '16px',
            'label': 'data(label)',
            'text-valign': 'center',
            'text-halign': 'center',
            'font-size': 12,
            'font-weight': 700,
            'text-max-width': 86,
            'color': payload.theme.foreground
          }}
        }},
        {{
          selector: 'node.state.initial',
          style: {{
            'border-color': payload.theme.ring,
            'border-width': 5
          }}
        }},
        {{
          selector: 'node.state.terminal',
          style: {{
            'background-color': payload.theme.accent,
            'border-color': payload.theme.accent,
            'color': payload.theme.accent_foreground,
            'width': 132,
            'height': 132
          }}
        }},
        {{
          selector: 'node.state.blocked',
          style: {{
            'border-color': payload.theme.error,
            'border-width': 5
          }}
        }},
        {{
          selector: 'node.execution',
          style: {{
            'shape': 'round-rectangle',
            'background-color': payload.theme.muted,
            'border-color': payload.theme.accent,
            'border-width': 2,
            'padding': '14px',
            'label': 'data(label)',
            'width': 'data(width)',
            'height': 'data(height)',
            'text-max-width': 'data(text_width)',
            'font-size': 12,
            'font-weight': 700,
            'text-wrap': 'wrap',
            'text-justification': 'center',
            'color': payload.theme.foreground
          }}
        }},
        {{
          selector: 'node.step',
          style: {{
            'shape': 'round-rectangle',
            'background-color': payload.theme.card,
            'border-color': payload.theme.border_strong,
            'border-width': 1.6,
            'padding': '10px',
            'label': 'data(label)',
            'width': 'data(width)',
            'height': 'data(height)',
            'text-max-width': 'data(text_width)',
            'font-size': 10,
            'line-height': 1.35,
            'text-wrap': 'wrap',
            'text-justification': 'center',
            'color': payload.theme.foreground
          }}
        }},
        {{
          selector: 'edge',
          style: {{
            'curve-style': 'bezier',
            'target-arrow-shape': 'triangle',
            'width': 1.8,
            'arrow-scale': 1.1,
            'line-color': payload.theme.border_strong,
            'target-arrow-color': payload.theme.border_strong
          }}
        }},
        {{
          selector: 'edge.attachment',
          style: {{
            'line-style': 'solid',
            'line-color': payload.theme.border,
            'target-arrow-color': payload.theme.border,
            'target-arrow-shape': 'triangle',
            'width': 1.6,
            'opacity': 0.92
          }}
        }},
        {{
          selector: 'edge.transition',
          style: {{
            'curve-style': 'unbundled-bezier',
            'control-point-distances': 'data(bend_distance)',
            'control-point-weights': 0.5,
            'line-color': payload.theme.accent,
            'target-arrow-color': payload.theme.accent,
            'label': 'data(label)',
            'font-size': 9,
            'color': payload.theme.foreground,
            'text-background-color': payload.theme.background,
            'text-background-opacity': 1,
            'text-background-padding': 3,
            'text-border-opacity': 0,
            'width': 2.2
          }}
        }},
        {{
          selector: 'edge.transition.to-terminal',
          style: {{
            'line-color': payload.theme.accent,
            'target-arrow-color': payload.theme.accent,
            'width': 2.2
          }}
        }},
        {{
          selector: 'edge.transition.to-blocked',
          style: {{
            'line-color': payload.theme.error,
            'target-arrow-color': payload.theme.error
          }}
        }},
        {{
          selector: 'edge.transition.self-loop',
          style: {{
            'curve-style': 'bezier',
            'line-color': payload.theme.accent_secondary,
            'target-arrow-color': payload.theme.accent_secondary
          }}
        }},
        {{
          selector: 'edge.dependency',
          style: {{
            'line-style': 'dashed',
            'line-color': payload.theme.border_strong,
            'target-arrow-color': payload.theme.border_strong
          }}
        }},
        {{
          selector: 'edge.workflow',
          style: {{
            'line-color': payload.theme.accent_secondary,
            'target-arrow-color': payload.theme.accent_secondary
          }}
        }},
        {{
          selector: ':selected',
          style: {{
            'overlay-color': payload.theme.ring,
            'overlay-opacity': 0.12,
            'overlay-padding': 10,
            'border-color': payload.theme.ring,
            'line-color': payload.theme.ring,
            'target-arrow-color': payload.theme.ring
          }}
        }}
      ],
      layout: {{
        name: 'preset',
        fit: true,
        padding: 120,
        animate: false
      }}
    }});

    cy.on('select', 'node, edge', (event) => updateDetails(event.target));
    cy.on('unselect', 'node, edge', () => {{
      const selected = cy.$(':selected');
      updateDetails(selected.nonempty() ? selected[0] : null);
    }});

    const openSidebar = () => {{
      body.classList.add('panel-open');
      toggleSidebarBtn.textContent = '×';
    }};

    const closeSidebar = () => {{
      body.classList.remove('panel-open');
      toggleSidebarBtn.textContent = '☰';
    }};

    toggleSidebarBtn.addEventListener('click', () => {{
      if (body.classList.contains('panel-open')) {{
        closeSidebar();
      }} else {{
        openSidebar();
      }}
    }});

    document.getElementById('fit-btn').addEventListener('click', () => cy.fit(undefined, 120));
    document.getElementById('reset-btn').addEventListener('click', () => {{
      cy.zoom(1);
      cy.center();
    }});
    document.getElementById('center-btn').addEventListener('click', () => cy.center());

    cy.ready(() => {{
      cy.fit(undefined, 120);
      updateDetails(null);
    }});
  </script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a whole skill flow to standalone HTML.")
    parser.add_argument("skill_path")
    parser.add_argument("-o", "--output", help="Write HTML to this file instead of stdout.")
    args = parser.parse_args()

    root = Path(args.skill_path).expanduser().resolve()
    payload = build_payload(root)
    html = html_document(payload, Path(__file__).resolve())
    if args.output:
        Path(args.output).expanduser().resolve().write_text(html, encoding="utf-8")
    else:
        print(html, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
