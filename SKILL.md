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

## Execution

Start every run with:

```bash
python <skill-framework-root>/scripts/skill_runtime.py init-run <skill-path>
```

Every command that advances work returns two protocol fields:

- `user_update`: the user-facing progress message to relay first
- `agent_next_action`: the exact next action to execute after that update

Relay `user_update.message` to the user, then automatically execute `agent_next_action.command` when it is present. The runtime still drives all subsequent execution — state routing, node planning, context slicing, result validation, and state transitions are all handled by the runtime scripts, not by the agent.

Only `blocked` waits for user input. Do not report completion until `transition` confirms a terminal state (`"status": "done"`).

## Available Scripts

```bash
python <skill-framework-root>/scripts/init_skill.py <skill-name> --path <skills-root>
python <skill-framework-root>/scripts/validate_skill.py <target-skill-path>
python <skill-framework-root>/scripts/validate_machine.py <target-skill-path>
python <skill-framework-root>/scripts/validate_contracts.py <target-skill-path>
python <skill-framework-root>/scripts/run_skill_evals.py <target-skill-path>
node <skill-framework-root>/scripts/render_skill_html.mjs <target-skill-path> -o skill-flow.html
```
