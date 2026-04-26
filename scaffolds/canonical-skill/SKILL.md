---
name: __SKILL_NAME__
description: __SKILL_DESCRIPTION__
---

# __SKILL_TITLE__

## Core Model

This scaffold is a runnable template default for a concrete `skill-framework/v1` skill.

Generated skills still interact with the agent through `skill-framework`'s `scripts/skill_runtime.py`. The runtime owns lifecycle transitions, node planning, context slicing, node-result recording, and run validation. The generated skill supplies the machine, graph, theory, rules, contracts, references, and evals that make those runtime decisions meaningful.

Replace the trigger description, purpose, references, examples, and evals with concrete skill content before treating the generated skill as finished. Read [theory.md](theory.md), [contracts/node-result.json](contracts/node-result.json), and [rules/global.json](rules/global.json) before changing behavior.

## Execution

Start each runtime-controlled run with the installed framework runtime:

```bash
python <skill-framework-root>/scripts/skill_runtime.py init-run <target-skill-path>
```

Every runtime command that advances work returns two protocol fields:

- `user_update`: relay `user_update.message` to the user first
- `agent_next_action`: execute `agent_next_action.command` next when it is present

Use the runtime to plan the active state graph, request the active context slice, record each node result, and apply the explicit machine transition. Do not execute node task work before `init-run` confirms a run id. Do not treat a node as complete until `record-node-result` returns `accepted: true`. Do not report completion until `transition` confirms a terminal state with `"status": "done"`.

Only `blocked` waits for user input. Generated skills should replace this scaffold's machine, graph, node contracts, rules, references, and evals with concrete behavior while preserving this runtime protocol.

## Available Scripts

Use scripts from the installed `skill-framework` directory:

```bash
python <skill-framework-root>/scripts/skill_runtime.py init-run <target-skill-path>
python <skill-framework-root>/scripts/validate_skill.py <target-skill-path>
python <skill-framework-root>/scripts/validate_machine.py <target-skill-path>
python <skill-framework-root>/scripts/validate_contracts.py <target-skill-path>
python <skill-framework-root>/scripts/run_skill_evals.py <target-skill-path>
node <skill-framework-root>/scripts/render_skill_html.mjs <target-skill-path> -o skill-flow.html
```
