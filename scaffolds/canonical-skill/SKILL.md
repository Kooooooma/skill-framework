---
name: __SKILL_NAME__
description: __SKILL_DESCRIPTION__
---

# __SKILL_TITLE__

## Core Model

This skill follows `skill-framework/v1`. Treat it as an LLM workflow program with the canonical framework structure.

Read [theory.md](theory.md) before changing the skill's behavior.
Use `scripts/skill_runtime.py` from `skill-framework` to read [skill.machine.json](skill.machine.json), [node.graph.json](node.graph.json), [context-policy.json](context-policy.json), and [runtime.json](runtime.json) before executing state or node work.
Read [contracts/node-result.json](contracts/node-result.json) before returning node output.
Read [rules/global.json](rules/global.json) before executing any node.

## Execution Workflow

1. Initialize or resume a runtime run.
2. Determine the current state from the runtime snapshot and replay log.
3. Ask the runtime for the active graph plan.
4. Ask the runtime for the current state/node/step context slice.
5. Load only the `agent_visible` resources returned by the context slice.
6. Execute each active node as a sequential micro-workflow with numbered steps.
7. Report node results with complete `step_results`.
8. Let the runtime validate and record node results before any state transition.
9. Follow only legal machine transitions.

## Invariants

- Do not bypass the theory layer.
- Do not encode lifecycle control only as prose.
- Do not encode node dependencies only as prose.
- Do not skip numbered node steps.
- Do not treat references as rules.
- Do not bulk-load all JSON specs into agent context. The runtime reads full specs; the executing agent/model receives only the current context slice.
- Do not claim completion without validation or a blocker report.

## Runtime

Use runtime commands from the installed framework skill. Replace `<skill-framework-root>` with the actual framework directory and `<target-skill-path>` with this skill directory:

```bash
python <skill-framework-root>/scripts/skill_runtime.py init-run <target-skill-path>
python <skill-framework-root>/scripts/skill_runtime.py status <target-skill-path> --run-id <run-id>
python <skill-framework-root>/scripts/skill_runtime.py plan <target-skill-path> --run-id <run-id>
python <skill-framework-root>/scripts/skill_runtime.py context <target-skill-path> --run-id <run-id> --node main --step load_required_context
```

## Completion Standard

This skill is ready when its behavior satisfies [evals/expected-behaviors.json](evals/expected-behaviors.json), and its high-risk rules have pressure scenarios in [evals/pressure-scenarios.md](evals/pressure-scenarios.md).
