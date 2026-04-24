# Skill Framework

`skill-framework` is a framework for creating agent skills as LLM workflow programs.

It treats a skill as a structured, runtime-controlled workflow rather than a prompt template. Every generated skill uses the same canonical structure; skills differ only by how many states, nodes, rules, artifacts, references, scripts, and evals they contain.

## Core Ideas

- **Theory first**: define purpose, domain model, invariants, failure theory, and judgment rubric before workflow details.
- **State machine lifecycle**: use `skill.machine.json` for lifecycle, gates, retry, blocked states, terminal states, and recovery.
- **DAG inside states**: use `node.graph.json` for state-internal node dependencies. DAG cycles are invalid.
- **Sequential nodes**: each node is a micro-workflow with ordered steps in `contracts/nodes.json`.
- **Rules as constraints**: scoped rules live under `rules/`, separate from reference material.
- **Progressive disclosure**: `context-policy.json` tells the runtime which resources are visible for the active state, node, and step.
- **Production runtime controls**: the runtime records events, snapshots state, computes node plans, slices context, validates node results, and supports replay.
- **Behavior evals**: pressure scenarios test expected and forbidden behavior.

## Repository Layout

```text
skill-framework/
  SKILL.md
  framework/
    *.schema.json
    philosophy.md
    ontology.yaml
  scaffolds/
    canonical-skill/
  references/
  scripts/
  evals/
  agents/
```

See [CONTRIBUTE.md](CONTRIBUTE.md) for the maintainer guide to every file, key JSON fields, the meaning of `skill-framework/v1`, and how the machine, graph, contracts, rules, context policy, runtime, scripts, and evals work together.

Generated skills use this canonical structure:

```text
my-skill/
  SKILL.md
  theory.md
  skill.machine.json
  node.graph.json
  context-policy.json
  runtime.json
  contracts/
  rules/
  references/
  scripts/
  evals/
  agents/
```

## Install As A Skill

`skill-framework` is itself a skill. Install it the same way you install any other skill: place this repository directory under a skills root that your agent runtime scans.

Example:

```text
<skills-root>/
  skill-framework/
    SKILL.md
    framework/
    scaffolds/
    scripts/
```

The exact skills root depends on your agent environment. The framework is path-neutral and does not require a fixed install location.

After installation, use it like a normal skill by asking your agent to use `skill-framework` for creating, updating, validating, or evolving skills.

Example prompts:

```text
Use skill-framework to create a new skill for API documentation workflows.
Use skill-framework to upgrade this existing skill into the canonical workflow-program structure.
Use skill-framework to validate this skill's machine, graph, contracts, rules, runtime, and evals.
```

## Create A Skill

In normal use, ask your agent to use `skill-framework`; the skill will guide the authoring workflow and call the appropriate scaffold, validation, and runtime tools when needed.

If you want to run the scaffold directly, use the framework from wherever it is installed:

```bash
python <skill-framework-root>/scripts/init_skill.py my-skill --path <skills-root>
```

Example:

```bash
python ./scripts/init_skill.py my-skill --path /tmp/skills
```

## Validate A Skill

In normal use, ask your agent to use `skill-framework` to validate the target skill. The direct commands are available when you want deterministic checks from a terminal:

```bash
python <skill-framework-root>/scripts/validate_skill.py <target-skill-path>
python <skill-framework-root>/scripts/validate_machine.py <target-skill-path>
python <skill-framework-root>/scripts/validate_contracts.py <target-skill-path>
python <skill-framework-root>/scripts/run_skill_evals.py <target-skill-path>
```

## Render Skill Diagrams

`skill-framework` renders whole-skill diagrams as standalone HTML pages.

Use the HTML renderer when you want one overall diagram that shows state-machine transitions, state-internal execution nodes, and workflow steps in a styled, navigable page:

```bash
python <skill-framework-root>/scripts/render_skill_html.py <target-skill-path> -o skill-flow.html
```

Notes:

- HTML is the official final artifact
- The renderer reads `skill.machine.json`, `node.graph.json`, and `contracts/nodes.json` directly
- The page is emitted as a single self-contained HTML file
- When the target skill has a `DESIGN.md`, the renderer reuses its design-token colors as the diagram theme when possible

## Runtime

In normal use, the installed `skill-framework` skill tells the agent when to initialize or resume a run, compute a node plan, request a context slice, record node results, and transition state.

The runtime is deterministic and local. It does not perform model reasoning. It controls execution state, graph planning, context slicing, transition legality, event logging, replay, and node-result acceptance.

```bash
python <skill-framework-root>/scripts/skill_runtime.py init-run <target-skill-path>
python <skill-framework-root>/scripts/skill_runtime.py status <target-skill-path> --run-id <run-id>
python <skill-framework-root>/scripts/skill_runtime.py plan <target-skill-path> --run-id <run-id>
python <skill-framework-root>/scripts/skill_runtime.py context <target-skill-path> --run-id <run-id> --node main --step load_required_context
python <skill-framework-root>/scripts/skill_runtime.py record-node-result <target-skill-path> --run-id <run-id> --node main --result <result.json>
python <skill-framework-root>/scripts/skill_runtime.py transition <target-skill-path> --run-id <run-id> --event success
python <skill-framework-root>/scripts/skill_runtime.py replay <target-skill-path> --run-id <run-id>
python <skill-framework-root>/scripts/skill_runtime.py validate-run <target-skill-path> --run-id <run-id>
```

## Validate This Framework

From this repository root:

```bash
python scripts/validate_skill.py .
python scripts/run_skill_evals.py .
```

## Notes

- Runtime-executable specifications are JSON so they can be parsed and analyzed deterministically.
- Markdown is used for theory, references, and human-readable pressure scenarios.
- The runtime can read full JSON specs, but the executing agent/model should only receive the active context slice.
- The framework is provider-neutral and path-neutral.

---

# Skill Framework 中文说明

`skill-framework` 是一个用于创建 agent skill 的框架。它的核心思想是：skill 不是提示词模板，而是一个 **LLM workflow program**。

每个由该框架生成的 skill 都使用同一套 canonical structure。不同 skill 的区别不在于结构等级，而在于包含多少 state、node、rule、artifact、reference、script 和 eval。

## 核心思想

- **Theory first**：先定义目的、领域模型、不变量、失败模式和判断标准，再写执行流程。
- **状态机管理生命周期**：用 `skill.machine.json` 管理生命周期、门禁、重试、阻塞状态、终止状态和恢复。
- **状态内部使用 DAG**：用 `node.graph.json` 表达 state 内部 node 依赖；DAG 不允许有环。
- **Node 内部顺序执行**：每个 node 是一个有序 micro-workflow，步骤定义在 `contracts/nodes.json`。
- **Rules 是约束**：硬规则放在 `rules/`，不要藏在 reference 里。
- **渐进式披露**：`context-policy.json` 定义当前 state、node、step 应该加载哪些资源。
- **生产级 runtime 控制**：runtime 记录事件、保存状态快照、生成 node plan、切分 context、校验 node result，并支持 replay。
- **行为 eval**：pressure scenarios 用来测试期望行为和禁止行为。

## 目录结构

```text
skill-framework/
  SKILL.md
  framework/
    *.schema.json
    philosophy.md
    ontology.yaml
  scaffolds/
    canonical-skill/
  references/
  scripts/
  evals/
  agents/
```

生成的 skill 使用如下结构：

```text
my-skill/
  SKILL.md
  theory.md
  skill.machine.json
  node.graph.json
  context-policy.json
  runtime.json
  contracts/
  rules/
  references/
  scripts/
  evals/
  agents/
```

## 作为 Skill 安装

`skill-framework` 本身就是一个 skill。安装方式和普通 skill 一样：把本仓库目录放到你的 agent runtime 会扫描的 skills root 下。

示例：

```text
<skills-root>/
  skill-framework/
    SKILL.md
    framework/
    scaffolds/
    scripts/
```

具体的 skills root 取决于你的 agent 环境。框架不绑定固定安装路径。

安装后，像使用普通 skill 一样使用它：让你的 agent 使用 `skill-framework` 来创建、更新、校验或演化 skill。

示例提示：

```text
Use skill-framework to create a new skill for API documentation workflows.
Use skill-framework to upgrade this existing skill into the canonical workflow-program structure.
Use skill-framework to validate this skill's machine, graph, contracts, rules, runtime, and evals.
```

## 创建 Skill

正常使用时，直接让 agent 使用 `skill-framework`；skill 会指导 authoring workflow，并在需要时调用 scaffold、validation 和 runtime 工具。

如果要直接从终端运行 scaffold，可以使用实际安装路径：

```bash
python <skill-framework-root>/scripts/init_skill.py my-skill --path <skills-root>
```

示例：

```bash
python ./scripts/init_skill.py my-skill --path /tmp/skills
```

## 校验 Skill

正常使用时，让 agent 使用 `skill-framework` 校验目标 skill。下面这些命令用于需要终端确定性检查的场景：

```bash
python <skill-framework-root>/scripts/validate_skill.py <target-skill-path>
python <skill-framework-root>/scripts/validate_machine.py <target-skill-path>
python <skill-framework-root>/scripts/validate_contracts.py <target-skill-path>
python <skill-framework-root>/scripts/run_skill_evals.py <target-skill-path>
```

## 渲染 Skill 流程图

`skill-framework` 现在把整体 skill 图渲染为单文件 HTML 页面。

如果你想得到完整总图，使用下面这条正式命令：

```bash
python <skill-framework-root>/scripts/render_skill_html.py <target-skill-path> -o skill-flow.html
```

说明：

- HTML 是正式最终交付产物
- 渲染器直接读取 `skill.machine.json`、`node.graph.json` 和 `contracts/nodes.json`
- 页面是单文件、自包含的 HTML
- 如果目标 skill 有 `DESIGN.md`，渲染器会尽量复用其中的设计 token 配色

## Runtime

正常使用时，已安装的 `skill-framework` skill 会告诉 agent 何时初始化或恢复 run、计算 node plan、请求 context slice、记录 node result，以及推进状态。

runtime 是确定性的本地执行控制框架。它不负责模型推理，而是负责状态、DAG 计划、context slicing、合法状态迁移、事件日志、replay 和 node result 接收校验。

```bash
python <skill-framework-root>/scripts/skill_runtime.py init-run <target-skill-path>
python <skill-framework-root>/scripts/skill_runtime.py status <target-skill-path> --run-id <run-id>
python <skill-framework-root>/scripts/skill_runtime.py plan <target-skill-path> --run-id <run-id>
python <skill-framework-root>/scripts/skill_runtime.py context <target-skill-path> --run-id <run-id> --node main --step load_required_context
python <skill-framework-root>/scripts/skill_runtime.py record-node-result <target-skill-path> --run-id <run-id> --node main --result <result.json>
python <skill-framework-root>/scripts/skill_runtime.py transition <target-skill-path> --run-id <run-id> --event success
python <skill-framework-root>/scripts/skill_runtime.py replay <target-skill-path> --run-id <run-id>
python <skill-framework-root>/scripts/skill_runtime.py validate-run <target-skill-path> --run-id <run-id>
```

## 校验本框架

在仓库根目录执行：

```bash
python scripts/validate_skill.py .
python scripts/run_skill_evals.py .
```

## 说明

- runtime 可执行规约使用 JSON，便于确定性解析和结构化分析。
- theory、references、pressure scenarios 使用 Markdown，便于人类和 agent 阅读。
- runtime 可以读取完整 JSON spec，但执行 agent/model 只应该接收当前 context slice。
- 框架不绑定具体模型供应商，也不绑定固定安装路径。
