# Examples

## One-State Skill

Use this shape for a focused skill with one execution path.

```text
machine:
  idle -> execute -> done

graph execute:
  main

node main:
  step 1: load inputs
  step 2: apply rules
  step 3: produce output
  step 4: validate result
```

This uses the same canonical structure as every other skill. It simply has fewer states and nodes.

## Composed Skill

Use this shape for a multi-step workflow with independent analysis nodes.

```text
machine:
  idle -> discover -> produce -> done

graph discover:
  inspect_files
  inspect_config
  summarize_context depends_on [inspect_files, inspect_config]

graph produce:
  draft_artifact depends_on [summarize_context]
  validate_artifact depends_on [draft_artifact]
```

The DAG isolates context and allows read-only deterministic nodes to run before creative agent/model nodes.

## Orchestrated Skill

Use this shape for a workflow with human gates, recovery, and review.

```text
machine:
  idle -> recover -> plan -> execute -> review -> writeback -> done
  execute -> blocked
  review -> execute
  blocked -> recover
```

Each state owns a node graph. The machine controls lifecycle and recovery; the DAG controls internal dependency order.

## Rule Loading Example

```yaml
context_policy:
  always_load:
    - theory.md
    - rules/global.json
  on_state:
    review:
      - rules/state/review.json
  on_node:
    draft_artifact:
      - rules/node/draft-artifact.json
      - contracts/artifacts.json
  on_step:
    write_artifact:
      - rules/step/write-artifact.json
```

Rules are loaded when they become enforceable.

## Node Step Example

```yaml
nodes:
  main:
    kind: agent
    execution: sequential
    purpose: Produce the target artifact without skipping prerequisite checks.
    inputs:
      - user_request
    outputs:
      - target_artifact
    workflow:
      - step: 1
        name: summarize_inputs
        action: Summarize the task-local inputs and missing information.
        done_when: Inputs and gaps are explicit.
      - step: 2
        name: check_blockers
        action: Apply global and node rules before drafting.
        stop_if: A required input or gate is missing.
        done_when: Blocker status is explicit.
      - step: 3
        name: produce_output
        action: Create the output according to the artifact contract.
        done_when: Output satisfies the required structure.
      - step: 4
        name: validate_handoff
        action: Return node result with step_results and validation notes.
        done_when: Each step status is reported.
```
