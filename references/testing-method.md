# Testing Method

## Pressure-Scenario Loop

Use a RED-GREEN-REFACTOR loop for skills.

1. RED: Write a realistic prompt where an agent without the skill would likely fail.
2. GREEN: Add the smallest framework rule, contract, node step, or validator that prevents the failure.
3. REFACTOR: Simplify wording, move deterministic pieces to scripts, and re-run scenarios.

## Scenario Shape

Each scenario should contain:

- `id`
- user-style `prompt`
- expected behavior
- forbidden behavior
- pass criteria

The scenario should test the skill's behavior, not whether the files contain specific phrases.

## Good Pressure Scenarios

Good scenarios force the agent to choose correctly under pressure:

- The user asks to skip a required gate.
- A canonical artifact already exists.
- A downstream artifact exists but an upstream artifact is missing.
- The user asks for a quick output that would bypass theory.
- A node has multiple steps and the agent tries to jump to the creative step.
- A deterministic tool fails and the agent tries to invent a success.

## Bad Pressure Scenarios

Avoid scenarios that only check shallow compliance:

- "Does SKILL.md exist?"
- "Does the skill mention DAG?"
- "Does the answer sound detailed?"

Structural checks belong in validators. Evals should test behavior.

## Validation Integrity

When forward-testing a skill, give the tester the skill and a realistic task. Do not pass your diagnosis, expected answer, or hidden rationale unless the eval explicitly requires it.

The goal is to learn whether the skill causes the desired behavior from fresh context.

## Regression Discipline

When a skill is updated, keep old pressure scenarios unless they no longer represent a valid requirement. A skill change that fixes one behavior but regresses another should not be accepted.

## Runtime Tests

For skills created by this framework, include runtime checks:

- initialize a run
- compute the active node plan
- compute a context slice
- record a valid node result
- reject an invalid node result
- transition through legal events
- reject illegal transitions
- replay the event log and compare it with the snapshot
