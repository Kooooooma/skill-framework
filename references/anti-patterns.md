# Anti-Patterns

## Prompt Pile

The skill is a long natural-language instruction file with no machine, graph, contracts, rules, scripts, or evals.

Why it fails: the executing agent/model must hold all control flow in attention and may skip or reorder instructions.

## Description Leakage

The frontmatter `description` explains the whole workflow.

Why it fails: the executing agent/model may act from metadata alone and never load the body.

## Giant SKILL.md

All domain knowledge and examples are placed in `SKILL.md`.

Why it fails: context is consumed before the agent knows which state, node, or step needs the information.

## Hidden Rules

Constraints are buried in prose references.

Why it fails: references inform behavior but do not reliably constrain behavior. Rules should be scoped and prioritized.

## DAG As Prose

The skill says "do A before B before C" but has no graph.

Why it fails: ordering cannot be validated, visualized, or used for context frontier loading.

## Node Without Steps

A node says "draft the artifact" but has no sequential workflow.

Why it fails: the agent may jump to output and skip prerequisite checks, summaries, or validation.

## Contract After Output

The skill defines the artifact shape after instructing the agent to write it.

Why it fails: contracts must shape generation, not merely audit it after drift occurs.

## Script Avoidance

The skill asks the executing agent/model to repeatedly do deterministic work, such as checking cycles or rendering files.

Why it fails: deterministic tasks should not vary across runs.

## Bulk Context Loading

The skill tells the executing agent/model to read every machine, graph, rule, contract, reference, and eval file before starting.

Why it fails: runtime specs should be parsed by runtime, and the executing agent/model should receive only the active context slice.

## No Recovery Model

The skill assumes the workflow starts fresh.

Why it fails: real project work often resumes after partial artifacts, failures, or user changes.

## Runtime-Less Recovery

The skill mentions recovery but has no event log, snapshot, replay, or transition guard.

Why it fails: recovery cannot be trusted when current state is not derivable from recorded events.

## Untested Guardrail

The skill states a hard rule but has no pressure scenario for that rule.

Why it fails: untested rules are aspirations, not reliable behavior.
