# Authoring Principles

## Start With Failure

Create a skill only when it prevents a recurring failure or unlocks a repeatable expert workflow. Before writing instructions, name the failure:

- skipped prerequisite
- overwritten artifact
- unstable output format
- context overload
- missing validation
- weak domain judgment
- fragile tool sequence

The skill should make that failure harder to repeat.

## Description Is A Trigger

Frontmatter `description` is for discovery and triggering only. It must not contain the full workflow.

Good description:

```yaml
description: Use when creating or upgrading skills as LLM workflow programs with state machines, DAG nodes, contracts, rules, validators, runtime controls, and evals.
```

Bad description:

```yaml
description: First define theory, then write a state machine, then create rules, then write evals...
```

If the description summarizes the whole workflow, an agent may act from the description and skip the body.

## Keep SKILL.md Thin

`SKILL.md` should contain:

- trigger-relevant overview after the skill loads
- core invariants
- authoring or execution workflow
- links to exact resources to read when needed

Move formal structure into machine and graph files. Move detailed domain material into references. Move repeatable logic into scripts. Move behavioral expectations into evals.

## Canonical Structure

Every skill should be created from the same canonical LLM workflow program structure:

- theory
- machine
- node graph
- node contracts
- rules
- context policy
- artifact contracts
- evals

Skills differ by the number of states, nodes, rules, artifacts, references, scripts, and evals. Do not create separate categories or lower-standard templates.

## State Machine Outside, DAG Inside

Use the state machine for lifecycle:

- user gates
- blocked states
- retry loops
- recovery
- terminal states

Use the DAG for work decomposition inside a state:

- dependency order
- parallelizable read-only analysis
- join points
- artifact flow
- context batch boundaries

## Node As Sequential Micro-Workflow

Each node must be internally sequential. Use numbered steps with explicit completion criteria.

Required node step fields:

- `step`
- `name`
- `action`
- `done_when`

Use `stop_if` when a condition must block continuation.

## Rules Are First-Class

Rules are constraints, not optional reading. Write them in `rules/` and load them by scope:

- global
- machine
- state
- node
- step

Rules must be phrased as enforceable statements. Avoid vague advice.

## Context Is Scheduled

Context should load in batches controlled by `context-policy.json`.

Default loading layers:

1. Always load theory and global rules.
2. Load state rules and contracts when entering a state.
3. Load node rules, node contract, and relevant artifacts before a node runs.
4. Load step rules only at the step that needs them.
5. Load references only when they materially affect current work.

The runtime may parse the full JSON specification, but the executing agent/model should receive only the active context slice. JSON spec files are not automatically agent-visible.

## Script Deterministic Work

Use scripts for:

- parsing skill files
- validating state transitions
- checking DAG cycles
- validating artifact sections
- rendering previews or graphs
- deterministic naming
- repeatable transforms

Do not ask the executing agent/model to repeatedly perform fragile deterministic logic in prose.

## Test Behavior, Not File Count

A skill is ready when evals demonstrate behavior. File presence is only a structural baseline.

Every high-risk rule should have at least one pressure scenario that would fail if the rule were ignored.
