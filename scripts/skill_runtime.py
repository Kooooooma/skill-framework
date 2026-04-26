#!/usr/bin/env python3
"""Production local runtime for skill-framework/v1 skills.

The runtime controls state transitions, node planning, context slicing, event logs,
snapshots, replay, loop guards, locks, and node-result acceptance. It does not
perform model reasoning.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from schema_validation import validate_schema_document


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def framework_schema_root() -> Path:
    return Path(__file__).resolve().parent.parent / "framework"


def atomic_write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def append_jsonl(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(data, sort_keys=True) + "\n")


@contextmanager
def run_lock(run_dir: Path, timeout: int):
    lock = run_dir / "run.lock"
    start = time.time()
    fd: int | None = None
    while True:
        try:
            fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"{os.getpid()} {now()}\n".encode())
            break
        except FileExistsError:
            if time.time() - start > timeout:
                raise SystemExit(f"Runtime lock timeout: {lock}")
            time.sleep(0.1)
    try:
        yield
    finally:
        if fd is not None:
            os.close(fd)
        try:
            lock.unlink()
        except FileNotFoundError:
            pass


def runtime_config(root: Path) -> dict[str, Any]:
    return load_json(root / "runtime.json").get("runtime", {})


def run_root(root: Path) -> Path:
    return root / runtime_config(root).get("run_dir", ".skill-framework/runs")


def run_dir(root: Path, run_id: str) -> Path:
    return run_root(root) / run_id


def event_path(root: Path, run_id: str) -> Path:
    return run_dir(root, run_id) / runtime_config(root).get("event_log", {}).get("path", "events.jsonl")


def state_path(root: Path, run_id: str) -> Path:
    return run_dir(root, run_id) / runtime_config(root).get("snapshot", {}).get("path", "state.json")


def node_plan_path(root: Path, run_id: str) -> Path:
    return run_dir(root, run_id) / runtime_config(root).get("node_plan", {}).get("path", "node-plan.json")


def node_result_dir(root: Path, run_id: str) -> Path:
    return run_dir(root, run_id) / runtime_config(root).get("node_results", {}).get("dir", "node-results")


def machine(root: Path) -> dict[str, Any]:
    return load_json(root / "skill.machine.json").get("machine", {})


def graph_spec(root: Path) -> dict[str, Any]:
    return load_json(root / "node.graph.json").get("graphs", {})


def node_contracts(root: Path) -> dict[str, Any]:
    return load_json(root / "contracts" / "nodes.json").get("nodes", {})


def new_event(event_type: str, from_state: str, **kwargs: Any) -> dict[str, Any]:
    event = {
        "event_id": uuid.uuid4().hex,
        "timestamp": now(),
        "type": event_type,
        "from_state": from_state,
    }
    event.update(kwargs)
    return event


def load_state(root: Path, run_id: str) -> dict[str, Any]:
    return load_json(state_path(root, run_id))


def save_state(root: Path, run_id: str, state: dict[str, Any]) -> None:
    state["updated_at"] = now()
    atomic_write(state_path(root, run_id), state)


def append_event(root: Path, run_id: str, event: dict[str, Any]) -> None:
    append_jsonl(event_path(root, run_id), event)


def read_events(root: Path, run_id: str) -> list[dict[str, Any]]:
    path = event_path(root, run_id)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def validate_runtime_artifacts(root: Path, run_id: str) -> list[str]:
    errors: list[str] = []
    schema_root = framework_schema_root()

    try:
        state_schema = load_json(schema_root / "runtime-state.schema.json")
        state = load_json(state_path(root, run_id))
    except Exception as exc:
        return [f"Unable to read runtime state: {exc}"]
    for error in validate_schema_document(state, state_schema):
        errors.append(f"state.json violates framework/runtime-state.schema.json: {error}")

    try:
        event_schema = load_json(schema_root / "runtime-event.schema.json")
        event_text = event_path(root, run_id).read_text(encoding="utf-8")
    except Exception as exc:
        errors.append(f"Unable to read runtime events: {exc}")
        return errors

    for line_number, line in enumerate(event_text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"events.jsonl line {line_number} is invalid JSON: {exc}")
            continue
        for error in validate_schema_document(event, event_schema):
            errors.append(f"events.jsonl line {line_number} violates framework/runtime-event.schema.json: {error}")

    return errors


def topo_plan(root: Path, state_name: str) -> list[str]:
    m = machine(root)
    states = m.get("states", {})
    graph_id = states.get(state_name, {}).get("graph")
    if not graph_id:
        return []
    graphs = graph_spec(root)
    nodes = graphs.get(graph_id, {}).get("nodes", {})
    ordered: list[str] = []
    seen: set[str] = set()
    visiting: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise SystemExit(f"DAG cycle detected at node: {node}")
        if node in seen:
            return
        visiting.add(node)
        for dep in nodes[node].get("depends_on", []):
            if dep not in nodes:
                raise SystemExit(f"Unknown dependency '{dep}' for node '{node}'")
            visit(dep)
        visiting.remove(node)
        seen.add(node)
        ordered.append(node)

    for node in nodes:
        visit(node)
    return ordered


def resolve_node_step(root: Path, node: str, step_name: str | None) -> dict[str, Any] | None:
    contract = node_contracts(root).get(node)
    if not contract:
        raise SystemExit(f"Unknown node contract: {node}")
    if step_name is None:
        return None
    for step in contract.get("workflow", []):
        if str(step.get("step")) == str(step_name) or step.get("name") == step_name:
            return step
    raise SystemExit(f"Unknown step for node '{node}': {step_name}")


def strip_fragment(path: str) -> str:
    return path.split("#", 1)[0]


def resource_exists(root: Path, path: str) -> bool:
    base = strip_fragment(path)
    if "*" in base:
        return True
    return (root / base).exists()


def context_slice(root: Path, state_name: str, node: str | None, step_name: str | None) -> dict[str, Any]:
    policy = load_json(root / "context-policy.json").get("context_policy", {})
    resources: list[dict[str, Any]] = []
    resources.extend(policy.get("always_load", []))
    resources.extend(policy.get("on_state", {}).get(state_name, []))
    if node:
        resources.extend(policy.get("on_node", {}).get(node, []))
    step = resolve_node_step(root, node, step_name) if node else None
    if step:
        resources.extend(policy.get("on_step", {}).get(step.get("name"), []))

    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, Any]] = []
    for resource in resources:
        key = (resource.get("path", ""), resource.get("audience", ""))
        if key in seen:
            continue
        seen.add(key)
        if resource.get("path") and not resource_exists(root, resource["path"]):
            raise SystemExit(f"Context resource does not exist: {resource['path']}")
        unique.append(resource)

    max_items = policy.get("max_context_items")
    if policy.get("forbidden_bulk_load") and max_items and len(unique) > max_items:
        raise SystemExit(f"Context slice exceeds max_context_items={max_items}: {len(unique)}")

    agent_visible = [r for r in unique if r.get("audience") in {"agent_visible", "both"}]
    runtime_only = [r for r in unique if r.get("audience") == "runtime_only"]
    do_not_load = policy.get("never_load_unless_requested", [])

    active_instruction: dict[str, Any] = {}
    active_rules: list[dict[str, Any]] = []
    if node:
        contract = node_contracts(root).get(node, {})
        active_instruction["node"] = node
        active_instruction["instruction"] = contract.get("instruction")
        if step:
            active_instruction["step"] = step
    for resource in unique:
        if resource.get("resource_type") == "rule":
            rule_path = root / strip_fragment(resource.get("path", ""))
            if rule_path.exists():
                for rule in load_json(rule_path).get("rules", []):
                    active_rules.append(rule)
    active_rules.sort(key=lambda item: item.get("priority", 9999))

    return {
        "state": state_name,
        "node": node,
        "step": step_name,
        "load": unique,
        "agent_visible": agent_visible,
        "runtime_only": runtime_only,
        "do_not_load": do_not_load,
        "active_instruction": active_instruction,
        "active_rules": active_rules,
    }


def status_for_state(root: Path, state: dict[str, Any]) -> dict[str, Any]:
    current = state["current_state"]
    m = machine(root)
    spec = m.get("states", {}).get(current, {})
    terminal = current in set(m.get("terminal", []))
    return {
        "run_id": state["run_id"],
        "current_state": current,
        "status": state["status"],
        "terminal": terminal,
        "allowed_transitions": spec.get("on", {}),
        "active_graph": spec.get("graph"),
        "next_nodes": topo_plan(root, current),
        "state_visits": state.get("state_visits", {}),
    }


def skill_name(root: Path) -> str:
    skill_file = root / "SKILL.md"
    try:
        text = skill_file.read_text(encoding="utf-8")
    except OSError:
        return root.name
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return root.name
    name = re.search(r"^name:\s*([^\n]+?)\s*$", match.group(1), re.MULTILINE)
    if not name:
        return root.name
    value = name.group(1).strip().strip("\"'")
    if value.startswith("__") and value.endswith("__"):
        return root.name
    return value or root.name


def prefix_user_message(root: Path, message: str) -> str:
    prefix = f"[{skill_name(root)}] "
    if message.startswith(prefix):
        return message
    return f"{prefix}{message}"


def make_user_update(message: str, *, wait_for_user_response: bool = False, **kwargs: Any) -> dict[str, Any]:
    update = {
        "message": message,
        "wait_for_user_response": wait_for_user_response,
    }
    update.update(kwargs)
    return update


def make_agent_next_action(description: str, command: str | None, **kwargs: Any) -> dict[str, Any]:
    action = {
        "description": description,
        "command": command,
    }
    action.update(kwargs)
    return action


def attach_runtime_protocol(
    payload: dict[str, Any],
    root: Path,
    *,
    user_message: str,
    action_description: str,
    command: str | None,
    wait_for_user_response: bool = False,
    user_extra: dict[str, Any] | None = None,
    action_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload["user_update"] = make_user_update(
        prefix_user_message(root, user_message),
        wait_for_user_response=wait_for_user_response,
        **(user_extra or {}),
    )
    payload["agent_next_action"] = make_agent_next_action(
        action_description,
        command,
        **(action_extra or {}),
    )
    return payload


def cmd_init_run(root: Path) -> int:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    rd = run_dir(root, run_id)
    rd.mkdir(parents=True, exist_ok=False)
    (node_result_dir(root, run_id)).mkdir(parents=True, exist_ok=True)
    cfg = runtime_config(root)
    initial = machine(root).get("initial")
    state = {
        "framework": "skill-framework/v1",
        "run_id": run_id,
        "skill_path": str(root),
        "current_state": initial,
        "status": "running",
        "state_visits": {initial: 1},
        "created_at": now(),
        "updated_at": now(),
    }
    with run_lock(rd, cfg.get("lock_timeout_seconds", 30)):
        event = new_event("run_initialized", initial, to_state=initial, details={"skill_path": str(root)})
        state["last_event_id"] = event["event_id"]
        atomic_write(state_path(root, run_id), state)
        append_event(root, run_id, event)
    script = Path(__file__).resolve()
    payload = {
        "run_id": run_id,
        "state": state,
    }
    attach_runtime_protocol(
        payload,
        root,
        user_message=f"Run initialized in state '{initial}'. Next, the runtime will generate the node execution plan for this state.",
        action_description=f"Generate the node execution plan for state '{initial}'.",
        command=f"{sys.executable} {script} plan {root} --run-id {run_id}",
    )
    print(json.dumps(payload, indent=2))
    return 0


def cmd_status(root: Path, run_id: str) -> int:
    print(json.dumps(status_for_state(root, load_state(root, run_id)), indent=2))
    return 0


def cmd_plan(root: Path, run_id: str) -> int:
    state = load_state(root, run_id)
    plan = {
        "run_id": run_id,
        "state": state["current_state"],
        "nodes": topo_plan(root, state["current_state"]),
        "created_at": now(),
    }
    cfg = runtime_config(root)
    with run_lock(run_dir(root, run_id), cfg.get("lock_timeout_seconds", 30)):
        atomic_write(node_plan_path(root, run_id), plan)
    script = Path(__file__).resolve()
    nodes = plan["nodes"]
    if nodes:
        attach_runtime_protocol(
            plan,
            root,
            user_message=(
                f"Planned state '{state['current_state']}'. Next, the runtime will request the context slice for node '{nodes[0]}'."
            ),
            action_description=f"Request the context slice for node '{nodes[0]}'.",
            command=f"{sys.executable} {script} context {root} --run-id {run_id} --node {nodes[0]}",
        )
    else:
        attach_runtime_protocol(
            plan,
            root,
            user_message=(
                f"State '{state['current_state']}' has no executable nodes. Next, the runtime will apply the appropriate transition event."
            ),
            action_description="Apply the appropriate transition event for this state.",
            command=f"{sys.executable} {script} transition {root} --run-id {run_id} --event <event>",
        )
    print(json.dumps(plan, indent=2))
    return 0


def cmd_context(root: Path, run_id: str, node: str | None, step: str | None) -> int:
    state = load_state(root, run_id)
    result = context_slice(root, state["current_state"], node, step)
    cfg = runtime_config(root)
    with run_lock(run_dir(root, run_id), cfg.get("lock_timeout_seconds", 30)):
        append_event(root, run_id, new_event("context_slice_computed", state["current_state"], node=node, details={"step": step}))
    script = Path(__file__).resolve()
    if node:
        attach_runtime_protocol(
            result,
            root,
            user_message=(
                f"Loaded the context slice for node '{node}' in state '{state['current_state']}'. Next, the agent will execute that node."
            ),
            action_description=(
                f"Read active_instruction and execute node '{node}' steps in order. "
                "Follow each step's action and done_when. "
                "Write your completed result to a JSON file, then submit it."
            ),
            command=f"{sys.executable} {script} record-node-result {root} --run-id {run_id} --node {node} --result <path-to-result.json>",
            action_extra={"result_schema": str(root / "contracts" / "node-result.json")},
        )
    print(json.dumps(result, indent=2))
    return 0


def transition_allowed(root: Path, state: dict[str, Any], event_name: str) -> tuple[str, str]:
    m = machine(root)
    current = state["current_state"]
    if current in set(m.get("terminal", [])):
        raise SystemExit(f"Cannot transition from terminal state: {current}")
    transitions = m.get("states", {}).get(current, {}).get("on", {})
    if event_name not in transitions:
        raise SystemExit(f"Illegal transition event '{event_name}' from state '{current}'")
    return current, transitions[event_name]


def enforce_loop_guards(root: Path, state: dict[str, Any], source: str, target: str) -> None:
    guards = runtime_config(root).get("loop_guards", {})
    max_visits = guards.get("max_state_visits", {})
    visits = dict(state.get("state_visits", {}))
    next_count = visits.get(target, 0) + 1
    if target in max_visits and next_count > max_visits[target]:
        raise SystemExit(f"Loop guard exceeded for state '{target}': {next_count}>{max_visits[target]}")
    if source == target:
        max_self = guards.get("max_consecutive_self_transitions")
        if max_self is not None:
            consecutive = state.get("consecutive_self_transitions", 0) + 1
            if consecutive > max_self:
                raise SystemExit(f"Self-transition guard exceeded for state '{target}': {consecutive}>{max_self}")


def cmd_transition(root: Path, run_id: str, event_name: str) -> int:
    cfg = runtime_config(root)
    rd = run_dir(root, run_id)
    with run_lock(rd, cfg.get("lock_timeout_seconds", 30)):
        state = load_state(root, run_id)
        source, target = transition_allowed(root, state, event_name)
        enforce_loop_guards(root, state, source, target)
        visits = dict(state.get("state_visits", {}))
        visits[target] = visits.get(target, 0) + 1
        state["state_visits"] = visits
        state["current_state"] = target
        state["consecutive_self_transitions"] = state.get("consecutive_self_transitions", 0) + 1 if source == target else 0
        state["status"] = "done" if target in set(machine(root).get("terminal", [])) else ("blocked" if target == "blocked" else "running")
        event = new_event("transition", source, to_state=target, transition_event=event_name)
        state["last_event_id"] = event["event_id"]
        save_state(root, run_id, state)
        append_event(root, run_id, event)
    script = Path(__file__).resolve()
    is_terminal = state["status"] == "done"
    if is_terminal:
        attach_runtime_protocol(
            state,
            root,
            user_message=f"Terminal state '{target}' reached. The run is complete.",
            action_description="No further action. The run is complete.",
            command=None,
        )
    elif target == "blocked":
        # Read blockers from the most recent node result so the agent can surface them immediately.
        latest_blockers: list[str] = []
        nr_dir = node_result_dir(root, run_id)
        if nr_dir.exists():
            node_files = sorted(nr_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
            if node_files:
                try:
                    latest_blockers = load_json(node_files[0]).get("blockers", [])
                except Exception:
                    pass
        attach_runtime_protocol(
            state,
            root,
            user_message="Run is blocked. The blockers below must be resolved before execution can continue.",
            action_description=(
                "Wait for the user's response. Do not continue until they confirm the blockers are resolved."
            ),
            command=None,
            wait_for_user_response=True,
            user_extra={"blockers": latest_blockers},
            action_extra={
                "resolution_command": f"{sys.executable} {script} transition {root} --run-id {run_id} --event resolved",
            },
        )
    else:
        attach_runtime_protocol(
            state,
            root,
            user_message=f"Entered state '{target}'. Next, the runtime will generate the node execution plan for this state.",
            action_description=f"Generate the node execution plan for state '{target}'.",
            command=f"{sys.executable} {script} plan {root} --run-id {run_id}",
        )

    print(json.dumps(state, indent=2))
    return 0


def validate_node_result(root: Path, node: str, result: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    contract = node_contracts(root).get(node)
    if not contract:
        return [f"Unknown node contract: {node}"]
    for field in ["node", "status", "outputs", "blockers", "validation_notes", "step_results", "recommended_transition"]:
        if field not in result:
            errors.append(f"Node result missing field: {field}")
    if result.get("node") != node:
        errors.append(f"Node result node mismatch: expected {node}, got {result.get('node')}")
    valid_status = load_json(root / "contracts" / "node-result.json").get("node_result", {}).get("status_values", [])
    if result.get("status") not in valid_status:
        errors.append(f"Invalid node result status: {result.get('status')}")
    expected_steps = [(step["step"], step["name"]) for step in contract.get("workflow", [])]
    actual_steps = [(step.get("step"), step.get("name")) for step in result.get("step_results", [])]
    if actual_steps != expected_steps:
        errors.append(f"step_results must exactly match node workflow steps: expected {expected_steps}, got {actual_steps}")
    return errors


def cmd_record_node_result(root: Path, run_id: str, node: str, result_path: str) -> int:
    result = load_json(Path(result_path).expanduser().resolve())
    cfg = runtime_config(root)
    rd = run_dir(root, run_id)
    with run_lock(rd, cfg.get("lock_timeout_seconds", 30)):
        state = load_state(root, run_id)
        errors = validate_node_result(root, node, result)
        if errors:
            append_event(root, run_id, new_event("node_result_rejected", state["current_state"], node=node, status="rejected", details={"errors": errors}))
            script = Path(__file__).resolve()
            payload = {
                "accepted": False,
                "errors": errors,
            }
            attach_runtime_protocol(
                payload,
                root,
                user_message=f"Node '{node}' result was rejected. Next, the agent must fix the result and resubmit it.",
                action_description="Fix the errors above and resubmit the node result.",
                command=f"{sys.executable} {script} record-node-result {root} --run-id {run_id} --node {node} --result <path-to-fixed-result.json>",
            )
            print(json.dumps(payload, indent=2))
            return 1
        target = node_result_dir(root, run_id) / f"{node}.json"
        atomic_write(target, result)
        append_event(root, run_id, new_event("node_result_recorded", state["current_state"], node=node, status=result.get("status"), details={"result_path": str(target)}))
    script = Path(__file__).resolve()
    recommended = result.get("recommended_transition", "<transition-event>")
    payload = {
        "accepted": True,
        "node": node,
    }
    attach_runtime_protocol(
        payload,
        root,
        user_message=f"Node '{node}' result was accepted. Next, the runtime will advance the state machine using transition '{recommended}'.",
        action_description=f"Advance the state machine using recommended transition '{recommended}'.",
        command=f"{sys.executable} {script} transition {root} --run-id {run_id} --event {recommended}",
    )
    print(json.dumps(payload, indent=2))
    return 0


def replay_state(root: Path, run_id: str) -> dict[str, Any]:
    events = read_events(root, run_id)
    if not events:
        raise SystemExit("Cannot replay run with no events")
    m = machine(root)
    current = m.get("initial")
    visits = {current: 1}
    status = "running"
    for event in events:
        if event["type"] == "run_initialized":
            current = event.get("to_state", current)
        elif event["type"] == "transition":
            transition_event = event.get("transition_event")
            target = m.get("states", {}).get(current, {}).get("on", {}).get(transition_event)
            if target != event.get("to_state"):
                raise SystemExit(f"Replay mismatch at event {event['event_id']}")
            current = target
            visits[current] = visits.get(current, 0) + 1
            status = "done" if current in set(m.get("terminal", [])) else ("blocked" if current == "blocked" else "running")
    return {"current_state": current, "status": status, "state_visits": visits}


def cmd_replay(root: Path, run_id: str) -> int:
    replayed = replay_state(root, run_id)
    print(json.dumps(replayed, indent=2))
    return 0


def cmd_validate_run(root: Path, run_id: str) -> int:
    artifact_errors = validate_runtime_artifacts(root, run_id)
    if artifact_errors:
        print(json.dumps({"valid": False, "errors": artifact_errors}, indent=2))
        return 1
    replayed = replay_state(root, run_id)
    snapshot = load_state(root, run_id)
    errors = []
    for key in ["current_state", "status"]:
        if snapshot.get(key) != replayed.get(key):
            errors.append(f"Snapshot {key}={snapshot.get(key)} does not match replay {replayed.get(key)}")
    if errors:
        print(json.dumps({"valid": False, "errors": errors, "replay": replayed, "snapshot": snapshot}, indent=2))
        return 1
    cfg = runtime_config(root)
    with run_lock(run_dir(root, run_id), cfg.get("lock_timeout_seconds", 30)):
        append_event(root, run_id, new_event("replay_validated", snapshot["current_state"], details={"status": snapshot["status"]}))
    print(json.dumps({"valid": True, "replay": replayed}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Production local runtime for skill-framework/v1 skills.")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ["init-run", "status", "plan", "context", "transition", "record-node-result", "replay", "validate-run"]:
        p = sub.add_parser(name)
        p.add_argument("skill_path")
        if name != "init-run":
            p.add_argument("--run-id", required=True)
        if name == "context":
            p.add_argument("--node")
            p.add_argument("--step")
        if name == "transition":
            p.add_argument("--event", required=True)
        if name == "record-node-result":
            p.add_argument("--node", required=True)
            p.add_argument("--result", required=True)
    args = parser.parse_args()
    root = Path(args.skill_path).expanduser().resolve()
    if args.command == "init-run":
        return cmd_init_run(root)
    if args.command == "status":
        return cmd_status(root, args.run_id)
    if args.command == "plan":
        return cmd_plan(root, args.run_id)
    if args.command == "context":
        return cmd_context(root, args.run_id, args.node, args.step)
    if args.command == "transition":
        return cmd_transition(root, args.run_id, args.event)
    if args.command == "record-node-result":
        return cmd_record_node_result(root, args.run_id, args.node, args.result)
    if args.command == "replay":
        return cmd_replay(root, args.run_id)
    if args.command == "validate-run":
        return cmd_validate_run(root, args.run_id)
    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
