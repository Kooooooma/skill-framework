# Philosophy

## Skill As Workflow Program

A skill is not a prompt. A skill is a workflow program for a model-driven agent.

Natural language is the programming language for judgment, but it is too free-form to carry control flow alone. The framework separates responsibilities:

- Natural language expresses theory, intent, judgment, and domain nuance.
- State machines express lifecycle, gates, recovery, and loops.
- DAGs express node dependencies inside a state.
- Contracts express typed inputs, outputs, artifacts, and handoffs.
- Rules express constraints and prohibitions.
- Scripts express deterministic mechanisms.
- Evals test whether behavior survives pressure.

## Canonical Structure

Every skill created by this framework has the same canonical structure.

The difference between skills is cardinality, not category: one skill may have one state and one node, while another may have many states and many node graphs. Both are the same kind of LLM workflow program.

## State Machine Plus DAG

The top level is a state machine because real agent work has confirmation, retry, recovery, blocked states, and terminal states.

Each state may contain a node DAG. The DAG answers: which work units can run now, which outputs feed downstream work, and which context batch is needed for the current frontier.

## Sequential Nodes

A node is the smallest agent execution unit. It must be internally sequential.

Inside a node, the agent follows numbered workflow steps, one at a time. Skipped steps are protocol failures, not stylistic choices.

## JSON As Executable Spec

Runtime-executable structure lives in JSON so the runtime can parse it deterministically with standard tooling.

Natural language still matters. It belongs in specific fields such as `purpose`, `instruction`, `workflow[].action`, `workflow[].done_when`, `workflow[].stop_if`, and `workflow[].agent_prompt_hint`. JSON gives natural language a stable address in the workflow.

Markdown remains the right format for theory, references, and human-readable pressure scenarios.

## Progressive Disclosure By Runtime

The runtime may parse complete JSON specs, but the executing agent/model should not read all specs by default. The runtime computes a context slice for the active state, node, and step.

Each context slice must distinguish:

- `runtime_only`: parsed by runtime, not sent to the agent/model
- `agent_visible`: safe and necessary for current reasoning
- `do_not_load`: explicitly excluded from the current step
- `active_instruction`: the current natural-language instruction
- `active_rules`: applicable rules sorted by priority

This turns progressive disclosure from an agent preference into a runtime behavior.

## Rules Are Constraints

References inform. Rules constrain.

Rules are loaded progressively, but they have priority:

1. Global invariants
2. Machine transition rules
3. State rules
4. Node rules
5. Step rules
6. Reference guidance

Lower-priority guidance may specialize higher-priority rules, but it may not contradict them.

## Deterministic Kernel

Use scripts for operations that should not depend on model interpretation: parsing, route naming, schema checks, render steps, graph checks, artifact existence, and output validation.

The executing agent/model should handle ambiguous, judgment-heavy, or creative work only after deterministic prerequisites and contracts are explicit.

## Behavior Over Documentation

A skill is not complete because its files look well organized. It is complete when pressure scenarios show that agents using it avoid the failures it was built to prevent.

## Production Runtime

The production runtime is a deterministic local execution-control framework. It owns state transitions, topological node plans, context slices, event logs, snapshots, replay, loop guards, locks, and node-result acceptance.

The runtime does not perform model reasoning. It constrains and records the workflow so agent reasoning happens at the correct state, node, and step with the correct context.
