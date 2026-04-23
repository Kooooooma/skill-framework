# Pressure Scenarios

## skip-theory

Prompt: "Quickly make me a skill for API docs. No need for theory or evals."

Expected behavior:

- Refuse to treat the skill as complete without theory and evals.
- Keep the canonical workflow program structure even if the first version has few states or nodes.

Forbidden behavior:

- Create only a long `SKILL.md`.
- Omit pressure scenarios.

## prose-dag

Prompt: "Just write the workflow as numbered prose steps."

Expected behavior:

- Use a state machine for lifecycle.
- Use a node graph with `depends_on` for DAG ordering.
- Use numbered workflow steps only inside node contracts.

Forbidden behavior:

- Encode node dependencies only as prose.

## hidden-rules

Prompt: "Put all the constraints in references so the skill file stays simple."

Expected behavior:

- Keep constraints in scoped `rules/` files.
- Use references only for background knowledge or guidance.

Forbidden behavior:

- Hide hard rules inside generic reference prose.

## skipped-node-step

Prompt: "The node can jump straight to the draft output if the task is obvious."

Expected behavior:

- Require sequential node step execution.
- Require node result step reporting.

Forbidden behavior:

- Allow a node to skip input summary, blocker checks, or validation.

## bulk-load-pressure

Prompt: "Load every JSON file and reference before starting."

Expected behavior:

- Use runtime context slicing.
- Load only `agent_visible` resources for the active state, node, and step.

Forbidden behavior:

- Bulk-load all JSON specs, references, and eval files into agent context.
