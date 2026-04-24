---
name: skill-framework
description: Use when creating, upgrading, validating, operating, or visualizing agent skills as LLM workflow programs.
---

# Skill Framework

## Core Model

This skill follows `skill-framework/v1` and is itself a framework-compliant LLM workflow program.

Use it for four capability branches:

- authoring: create, scaffold, upgrade, or refactor a skill
- validation: run framework validators or eval checks
- runtime: inspect or operate the deterministic skill runtime
- diagrams: render a whole-skill flow diagram as standalone `HTML`

Read [theory.md](theory.md) before changing capability behavior.
Use runtime-controlled specs in [skill.machine.json](skill.machine.json), [node.graph.json](node.graph.json), [context-policy.json](context-policy.json), and [runtime.json](runtime.json) to determine legal execution.
Read [contracts/node-result.json](contracts/node-result.json) before returning node output.
Read [rules/global.json](rules/global.json) before executing any node.

## Execution Workflow

1. Classify the request into authoring, validation, runtime, or diagram rendering.
2. Initialize or resume runtime state for the active branch when runtime control is needed.
3. Determine the active state, graph, node plan, and context slice from the framework specs.
4. Load only the `agent_visible` resources needed for the active state and node.
5. Execute each active node as a sequential micro-workflow with numbered steps.
6. Return contract-bound node results with complete outputs, blockers, and step results.
7. Let the runtime and contracts enforce validation before any state transition.
8. Produce explicit artifacts for validation, runtime, or HTML diagram work instead of prose-only completion.

## Invariants

- Treat every skill as an LLM workflow program, not a prompt template.
- Keep trigger language in frontmatter `description`; keep formal behavior in machine, graph, contracts, rules, runtime, and scripts.
- Preserve existing authoring, validation, and runtime behavior while evolving the framework.
- Generate diagram artifacts directly as standalone `HTML`.
- Treat missing HTML-render dependencies as a blocker; do not fall back to `DOT` or `SVG`.

## Runtime

```bash
python <skill-framework-root>/scripts/init_skill.py my-skill --path <skills-root>
python <skill-framework-root>/scripts/validate_skill.py <target-skill-path>
python <skill-framework-root>/scripts/validate_machine.py <target-skill-path>
python <skill-framework-root>/scripts/validate_contracts.py <target-skill-path>
python <skill-framework-root>/scripts/run_skill_evals.py <target-skill-path>
python <skill-framework-root>/scripts/render_skill_html.py <target-skill-path> -o skill-flow.html
python <skill-framework-root>/scripts/skill_runtime.py init-run <target-skill-path>
```

## Completion Standard

This skill is ready when its capability routing, authoring behavior, validation behavior, runtime behavior, and HTML diagram behavior satisfy [evals/expected-behaviors.json](evals/expected-behaviors.json), and its high-risk invariants remain covered by [evals/pressure-scenarios.md](evals/pressure-scenarios.md).
