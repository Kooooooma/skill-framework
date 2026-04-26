# Theory

## Purpose

__SKILL_PURPOSE__

## Domain Model

Use this section as a template default. Replace the generic skill nouns below with the concrete requests, artifacts, constraints, and domain objects that matter for the generated skill.

- `user_request`: The concrete requests that should trigger this skill.
- `state`: The lifecycle phase from `skill.machine.json`.
- `node`: The execution unit inside the current state's graph.
- `step`: A sequential action inside a node.
- `result`: The structured handoff recorded by the runtime after node execution.

## Invariants

Keep the framework invariants and add the domain invariants that make the concrete skill safe and useful.

- The skill must follow the state machine before executing node work.
- The skill must follow node graph dependencies before choosing node order.
- Each node must execute its steps sequentially.
- Hard constraints belong in `rules/`, not only in references or examples.
- Deterministic validation failures must be reported as blockers or revisions.
- Runtime reads complete JSON specs, while the executing agent/model receives only the active context slice.

## Failure Theory

Start from these default failure modes, then replace or extend them with the concrete ways this skill can go wrong.

This skill exists to prevent:

- acting from trigger metadata without loading the skill body
- skipping prerequisite checks
- mixing lifecycle control with creative output
- losing context discipline by loading every resource at once
- letting the executing agent/model read runtime-only JSON instead of a context slice
- producing outputs without contract validation

## Judgment Rubric

Use this as a default rubric until the generated skill defines sharper domain-specific standards.

Good execution is:

- state-aware
- contract-bound
- context-efficient
- runtime-recorded
- explicit about blockers
- validated before completion
