# Contribute

This document explains what each `skill-framework` file is for, what the important fields mean, and how the files collaborate so future contributors can extend the framework without weakening its workflow-program model.

<iframe src="assets/skill-framework-flow.html" title="Skill Framework Flow" style="width:100%;height:720px;border:2px solid #79747E;border-radius:24px;background:#FFFBFE;"></iframe>

[Open the standalone HTML diagram](assets/skill-framework-flow.html)

The diagram above is generated from `skill.machine.json`, `node.graph.json`, and `contracts/nodes.json` through the framework's own HTML rendering path. Read it first to get the lifecycle and branch structure, then use the sections below for the detailed file-by-file semantics. Execution-node workflow steps are rendered directly as graph nodes, and when `DESIGN.md` is present the renderer reuses its design-token colors as the page theme.

## Mental Model

`skill-framework` has two roles:

1. It is the framework used to author and validate other skills.
2. It is now also a framework-compliant skill itself.

That means the repository contains both:

- framework assets and scripts used by other skills
- root-level workflow-program files that describe how `skill-framework` itself routes requests

## What `skill-framework/v1` Means

The `"framework": "skill-framework/v1"` field is the framework identifier and version marker for runtime-executable specs.

It is not decorative. It tells readers and tools which spec family a JSON file belongs to. Today the validators do not enforce a specific literal value, but the framework, scaffolds, generated skills, runtime script help text, and docs all consistently use `skill-framework/v1`.

Keep it for now because:

- it makes the spec family explicit
- it leaves room for future incompatible revisions
- it keeps generated skills and the framework self-description aligned

Do not remove it casually across the repo unless you are intentionally changing the framework versioning strategy everywhere.

## Repository Map

### Root skill files

- `SKILL.md`: Human-facing trigger and operating guide for the `skill-framework` skill.
- `theory.md`: Why the root skill exists, what capability branches it has, and the invariants it must preserve.
- `skill.machine.json`: The lifecycle state machine for `skill-framework` itself.
- `node.graph.json`: The per-state DAG definitions for the root skill.
- `context-policy.json`: Which resources are visible in each state, node, and step.
- `runtime.json`: Deterministic runtime configuration for root-skill execution.

### Contracts

- `contracts/nodes.json`: Sequential micro-workflows for each root-skill node.
- `contracts/artifacts.json`: What root-skill artifacts must exist and what they mean.
- `contracts/node-result.json`: Required shape of every node result.
- `contracts/runtime-state.json`: Required shape of persisted runtime state.
- `contracts/runtime-event.json`: Required shape of runtime event log entries.

### Rules

- `rules/global.json`: Cross-cutting invariants that cannot be bypassed.
- `rules/state/execute.json`: State-scoped execution constraints.
- `rules/node/main.json`: Node-scoped constraints shared by active nodes.
- `rules/step/validate-and-handoff.json`: Final handoff constraints.

### Framework assets

- `framework/*.schema.json`: Structural schemas for runtime-executable specs.
- `framework/philosophy.md`: Core framework design principles.
- `framework/ontology.yaml`: Canonical naming and concept definitions.

### References

- `references/authoring-principles.md`: How to write good framework-compliant skills.
- `references/testing-method.md`: How to think about evals and testing.
- `references/anti-patterns.md`: Common failure patterns the framework exists to prevent.
- `references/examples.md`: Representative structural patterns.

### Scripts

- `scripts/init_skill.py`: Scaffold a new canonical skill.
- `scripts/validate_skill.py`: Full validator.
- `scripts/validate_machine.py`: Focused machine and graph validation.
- `scripts/validate_contracts.py`: Focused contracts, rules, and context-policy validation.
- `scripts/run_skill_evals.py`: Eval definition checks.
- `scripts/skill_runtime.py`: Deterministic local runtime.
- `scripts/render_skill_html.py`: Render the whole skill flow to a standalone HTML page.

### Evals

- `evals/expected-behaviors.json`: Structured expected and forbidden behaviors.
- `evals/pressure-scenarios.md`: Human-readable pressure scenarios matching those ids.
- `evals/framework-pressure-scenarios.md`: Additional framework-level pressure scenarios.

### Scaffolds

- `scaffolds/canonical-skill/`: The baseline structure copied into generated skills.

### Agent interface

- `agents/metadata.json`: UI-facing and invocation-facing metadata for the skill.

## Root Skill Workflow

The root `skill-framework` skill is intentionally minimal and request-routed.

Machine states:

- `route_request`: classify the request
- `author`: create or evolve skills
- `validate`: validate skills
- `runtime`: operate the deterministic runtime
- `render_diagram`: generate standalone HTML
- `blocked`: stop on missing prerequisites
- `done`: terminal state

The important design rule is that `render_diagram` is an independent branch. It adds diagram rendering without changing the meaning of existing authoring, validation, or runtime requests.

## Important File Semantics

### `skill.machine.json`

Important fields:

- `machine.initial`: first lifecycle state
- `machine.terminal`: terminal states
- `machine.states.<state>.purpose`: why the state exists
- `machine.states.<state>.graph`: which DAG to run inside the state
- `machine.states.<state>.on`: legal transitions keyed by event name
- `machine.states.<state>.recovery`: how the runtime should think about resume or replay

Meaning:

- the machine controls lifecycle and gating
- it does not define node order inside a state
- event labels in `on` become the legal transition vocabulary

### `node.graph.json`

Important fields:

- `graphs.<graph_id>.execution.mode`: DAG execution mode
- `graphs.<graph_id>.nodes.<node>.contract`: pointer into `contracts/nodes.json`
- `graphs.<graph_id>.nodes.<node>.depends_on`: DAG dependencies
- `graphs.<graph_id>.nodes.<node>.writes`: logical write set for conflict checking

Meaning:

- one graph belongs to one machine state
- DAG ordering lives here, not in prose
- node dependencies are structural and validator-visible

### `contracts/nodes.json`

Important fields:

- `kind`: execution unit type
- `execution`: must be `sequential`
- `purpose`: why the node exists
- `instruction`: branch-specific invariant guidance
- `inputs` / `outputs`: logical interface of the node
- `allowed_reads` / `allowed_writes`: resources the node may touch
- `workflow`: numbered micro-workflow steps
- `workflow[].stop_if`: explicit blocking condition
- `workflow[].done_when`: concrete completion signal
- `validators`: contracts used to validate outputs

Meaning:

- this is the executable contract for node behavior
- numbered steps are the only valid place for intra-node ordering
- if a node changes shape, update both its graph reference and contract

### `context-policy.json`

Important fields:

- `always_load`: resources always visible
- `on_state`: resources loaded on entering a state
- `on_node`: resources loaded for a specific node
- `on_step`: resources loaded only for a specific step
- `never_load_unless_requested`: resources kept out of normal execution
- `audience`: `agent_visible`, `runtime_only`, or `both`

Meaning:

- this file prevents context overload
- runtime may know the whole spec, but the executing agent should only see the active slice
- every added script, reference, or contract should be placed deliberately in this schedule

### `runtime.json`

Important fields:

- `run_dir`: where run data lives
- `event_log`: append-only event storage
- `snapshot`: persisted state snapshot
- `node_plan`: topological node plan file
- `node_results`: persisted node-result directory and acceptance settings
- `loop_guards`: anti-loop controls
- `context_slicing`: visibility and batching controls

Meaning:

- this is deterministic runtime policy, not agent guidance prose
- if lifecycle behavior changes, runtime expectations usually need to change too

### `contracts/artifacts.json`

Important fields:

- `path`: where the artifact lives
- `kind`: markdown, json, script, or other asset type
- `required`: whether the artifact must exist
- `sections`: required markdown sections when applicable
- `validator`: focused validator attached to the artifact

Meaning:

- this file explains what “complete” means for root artifacts
- use it when adding new root-level executable specs or required docs

### `rules/*.json`

Important fields:

- `id`: stable rule identifier
- `scope`: global, state, node, or step
- `applies_to`: target scope when needed
- `priority`: rule precedence hint
- `statement`: enforceable requirement
- `forbidden`: optional examples of what violates the rule

Meaning:

- rules are hard constraints, not background explanation
- if a constraint matters to execution, put it here rather than only in prose

### `evals/*`

Important fields:

- `expected-behaviors.json.scenarios[].id`: stable scenario id
- `prompt`: pressure prompt
- `expected_behavior`: what must happen
- `forbidden_behavior`: what must not happen
- `pass_criteria`: what success looks like

Meaning:

- JSON evals are the structured source of truth
- markdown pressure scenarios should mirror the same ids for human review

### `agents/metadata.json`

Important fields:

- `display_name`: UI name
- `short_description`: short scan-friendly summary
- `default_prompt`: default execution bias after trigger
- `allow_implicit_invocation`: whether the skill may be auto-triggered

Meaning:

- this file helps the agent know how to use the skill once triggered
- it does not replace the need for `SKILL.md` frontmatter description

## How The Files Work Together

The collaboration chain is:

1. `SKILL.md` frontmatter triggers the skill.
2. `agents/metadata.json` biases default usage after trigger.
3. `skill.machine.json` decides lifecycle state.
4. `node.graph.json` selects DAG ordering inside that state.
5. `contracts/nodes.json` defines what each node must do, step by step.
6. `rules/*.json` constrain what is allowed at global, state, node, and step scope.
7. `context-policy.json` decides which of those resources the agent/runtime can see at each moment.
8. `runtime.json` defines deterministic execution behavior and persistence.
9. `contracts/*` define what valid artifacts, node results, and runtime objects look like.
10. `scripts/*` perform deterministic work.
11. `evals/*` test whether the whole behavior still matches the intended model.

If any one of these layers is changed in isolation, check whether the adjacent layers also need updates. Common examples:

- new state -> update machine, graph, context policy, runtime loop guards, and likely evals
- new node -> update graph, node contract, context policy, and possibly rules
- new deterministic script -> update docs, context policy, and sometimes artifact contracts
- new output artifact -> update artifact contracts and eval expectations

## Contributor Guidelines

- Keep frontmatter `description` trigger-focused. It should say when to use the skill, not how to execute it.
- Add new capabilities as independent workflow branches when possible instead of overloading an existing branch.
- Prefer adding deterministic scripts over embedding repeatable procedures in long prose.
- Validate the root `skill-framework` skill after structural changes.
- Validate the canonical scaffold when changes affect generated-skill expectations.
- When changing the meaning of a spec field, update both docs and validators together.

## Recommended Checks

For root-skill changes:

```bash
python scripts/validate_skill.py .
python scripts/validate_machine.py .
python scripts/validate_contracts.py .
python scripts/render_skill_html.py . -o /tmp/skill-framework-flow.html
```

For scaffold-impacting changes:

```bash
python scripts/validate_skill.py scaffolds/canonical-skill
```
