# Theory

## Purpose

__SKILL_PURPOSE__

## Domain Model

- `user_request`: The task or intent that triggers the skill.
- `state`: The current lifecycle phase from `skill.machine.json`.
- `node`: The smallest execution unit inside the current state's DAG.
- `step`: A sequential action inside a node.
- `result`: The structured handoff produced by node execution.

## Invariants

- The skill must follow the state machine before executing node work.
- The skill must follow node graph dependencies before choosing node order.
- Each node must execute its steps sequentially.
- Hard constraints belong in `rules/`, not only in references.
- Deterministic validation failures must be reported as blockers or revisions.
- Runtime reads complete JSON specs, while the executing agent/model receives only the active context slice.

## Failure Theory

This skill exists to prevent:

- acting from trigger metadata without loading the skill body
- skipping prerequisite checks
- mixing lifecycle control with creative output
- losing context discipline by loading every resource at once
- letting the executing agent/model read runtime-only JSON instead of a context slice
- producing outputs without contract validation

## Judgment Rubric

Good execution is:

- state-aware
- contract-bound
- context-efficient
- runtime-recorded
- explicit about blockers
- validated before completion
