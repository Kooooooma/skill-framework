---
name: skill-framework
description: Framework for creating, updating, validating, and evolving agent skills as LLM workflow programs. Use when designing a new skill, upgrading an existing skill, creating reusable skill scaffolds, adding skill contracts, defining skill state machines or node DAGs, implementing runtime context slicing, or evaluating skill behavior with pressure scenarios.
---

# Skill Framework

## Core Model

Treat every skill as an LLM workflow program. Every skill created by this framework has the same canonical structure; skills differ only by the number of states, nodes, rules, artifacts, references, scripts, and evals they contain.

Required layers:

1. Theory: purpose, domain model, invariants, failure theory, and judgment rubric.
2. Machine: lifecycle states, gates, recovery, retries, blocked states, and terminal states.
3. Graph: DAG of nodes inside each state, executed in topological order.
4. Node contracts: each node is a strictly sequential micro-workflow with numbered steps.
5. Rules: global, state, node, and step constraints loaded as first-class resources.
6. Context policy: progressive batch loading by state, node, and step.
7. Runtime: deterministic state transitions, topological node planning, context slicing, event logs, replay, recovery, and node result acceptance.
8. Deterministic tooling: scripts and validators for repeatable logic.
9. Evals: pressure scenarios and expected or forbidden behaviors.

Read [framework/philosophy.md](framework/philosophy.md) before designing or revising framework-level behavior.
Read [framework/ontology.yaml](framework/ontology.yaml) before naming new framework concepts.
Read [references/authoring-principles.md](references/authoring-principles.md) before creating or updating a skill.
Read [references/testing-method.md](references/testing-method.md) before writing evals.
Read [references/anti-patterns.md](references/anti-patterns.md) before accepting a skill as complete.
Read [references/examples.md](references/examples.md) when choosing how many states, nodes, rules, artifacts, and evals the skill needs.

## Authoring Workflow

When creating or upgrading a skill, do this in order:

1. Define the failure mode the skill prevents. If there is no concrete failure mode, stop and clarify the skill's purpose.
2. Write the theory layer before writing workflow instructions.
3. Define invariants that cannot be overridden by lower-level rules.
4. Define the state machine before defining node details.
5. Define each state's node DAG using `depends_on` in `node.graph.json`; do not encode DAG ordering as prose.
6. Define each node as `execution: sequential` with numbered workflow steps.
7. Define rules as constraints, not reference prose.
8. Define artifacts and node result contracts before writing generation guidance.
9. Define context policy so rules, references, artifacts, scripts, and runtime specs load only when needed.
10. Define runtime guards, event schema, replay behavior, and context slicing rules.
11. Add deterministic scripts for parsing, rendering, validation, naming, and repeatable transformations.
12. Add pressure scenarios that test whether the skill prevents known failures.
13. Validate the skill and runtime behavior with the bundled scripts before treating it as ready.

## Scaffold

Use `scripts/init_skill.py` from the actual installed framework location to create a new framework-compliant skill:

```bash
python <skill-framework-root>/scripts/init_skill.py my-skill --path <skills-root>
```

The generated skill has the canonical LLM workflow program structure:

- one machine
- three starter states
- one node DAG
- one sequential node
- scoped starter rules
- starter contracts, context policy, runtime config, and evals

Add more states, nodes, artifacts, rules, scripts, references, or evals when the skill's domain requires them. Do not change the canonical structure.

## Validation

Run the full validator after creating or changing a framework-compliant skill:

```bash
python <skill-framework-root>/scripts/validate_skill.py <target-skill-path>
```

Use focused helpers when debugging:

```bash
python <skill-framework-root>/scripts/validate_machine.py <target-skill-path>
python <skill-framework-root>/scripts/validate_contracts.py <target-skill-path>
python <skill-framework-root>/scripts/render_skill_graph.py <target-skill-path>
python <skill-framework-root>/scripts/run_skill_evals.py <target-skill-path>
python <skill-framework-root>/scripts/skill_runtime.py init-run <target-skill-path>
```

## Invariants

- Do not reduce the framework to prompt templates.
- Do not write detailed workflow into frontmatter `description`; use it only for triggering.
- Do not let `SKILL.md` become the whole system. Move formal structure into machine, graph, rules, contracts, scripts, and evals.
- Do not model the top-level lifecycle as a DAG when user confirmation, recovery, retry, or blocked states exist. Use a state machine and put DAGs inside states.
- Do not allow unordered prose inside a node. Node internals must be sequential workflow steps.
- Do not treat rules as background references. Rules are constraints with priority and scope.
- Do not make the executing agent/model load every JSON spec. The runtime reads complete specs; the agent/model receives only the current context slice.
- Do not rely on natural language for deterministic operations that can be scripted or validated.
- Do not accept a skill without pressure scenarios that test the behaviors it exists to enforce.

## Completion Standard

A framework-compliant skill is ready only when:

- its theory explains why the workflow exists
- its machine defines the lifecycle
- its graph defines node dependencies
- its node contracts define sequential steps
- its rules define constraints by scope
- its context policy supports progressive batch loading
- its runtime can initialize, plan, slice context, transition, accept node results, replay events, and validate run state
- its artifacts and node results are contract-bound
- its scripts validate deterministic parts
- its evals test expected and forbidden behavior
