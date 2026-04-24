# Theory

## Purpose

Create, validate, operate, evolve, and visualize agent skills as deterministic LLM workflow programs so skill behavior is carried by explicit theory, state machines, node DAGs, contracts, rules, and runtime controls rather than ad hoc prompt interpretation.

## Domain Model

- `request_route`: The classified intent for the current `skill-framework` request.
- `authoring_request`: A request to create, upgrade, or evolve a skill as a workflow program.
- `validation_request`: A request to validate machine, contracts, rules, context policy, or evals for a skill.
- `runtime_request`: A request to use runtime controls such as run initialization, planning, context slicing, or replay.
- `diagram_request`: A request to render a whole-skill flow diagram as a standalone HTML artifact.
- `diagram_artifacts`: The generated `.html` output for a target skill.

## Invariants

- `skill-framework` must preserve its existing authoring, validation, and runtime capabilities.
- Request routing must happen before any specialized branch work begins.
- Whole-skill diagram rendering is a separate capability branch and must not change the semantics of authoring, validation, or runtime requests.
- Diagram rendering must generate HTML directly from the skill JSON specifications.
- HTML rendering requires the bundled browser graph libraries; missing render dependencies is a blocker, not a reason to fall back to DOT or SVG.

## Failure Theory

This skill exists to prevent:

- vague routing where the agent guesses between authoring, validation, runtime, and rendering behaviors
- diagram requests being handled as ad hoc prose instead of a repeatable HTML generation pipeline
- rendering flows that fall back to DOT or SVG instead of the official HTML route
- new diagram capability work accidentally changing the meaning of existing `skill-framework` requests

## Judgment Rubric

Good execution is:

- intent-routed
- capability-preserving
- script-aware
- explicit about blockers
- deterministic about HTML diagram artifacts
