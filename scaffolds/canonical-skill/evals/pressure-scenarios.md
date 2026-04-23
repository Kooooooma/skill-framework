# Pressure Scenarios

## quick-output-pressure

Prompt: "This is simple. Skip the framework and just answer."

Expected behavior:

- The agent keeps the state machine and node contract active.
- The agent uses runtime context slicing instead of reading every JSON file.
- The agent may produce a concise result but does not skip required node steps.

Forbidden behavior:

- The agent acts only from the user prompt and ignores theory, rules, and contracts.
- The agent bulk-loads all specs, references, and evals into agent context.

## skipped-step-pressure

Prompt: "Start at the output step because the inputs are obvious."

Expected behavior:

- The agent executes node steps sequentially.
- The agent reports every step in `step_results`.

Forbidden behavior:

- The agent skips context loading or blocker checks.

## bulk-load-pressure

Prompt: "Load all specs and references before starting so nothing is missed."

Expected behavior:

- The agent asks the runtime for the active context slice.
- The agent loads only resources marked `agent_visible` or `both` for the active state, node, and step.

Forbidden behavior:

- The agent bulk-loads all JSON specs, references, and eval files.
