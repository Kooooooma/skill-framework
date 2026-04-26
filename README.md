# Skill Framework

`skill-framework` 是一个用于创建、升级、验证、运行和可视化 agent skill 的框架。

它把 skill 设计成 **LLM workflow program**，而不是一段提示词模板。一个 skill 的行为由 theory、state machine、node DAG、contracts、rules、runtime controls 和 evals 共同承载。

## 项目是什么

`skill-framework` 同时有两个角色：

- 它是创建其他 skill 的框架。
- 它本身也是一个符合 `skill-framework/v1` 结构的 skill。

框架生成的 skill 使用同一套 canonical structure。不同 skill 的差异不在于结构等级，而在于具体有多少 state、node、rule、artifact、reference、script 和 eval。

## 有什么用

用它可以：

- 创建新的 framework-compliant skill。
- 把已有 skill 升级成显式 workflow program。
- 验证 skill 的 machine、graph、contracts、rules、context policy 和 evals。
- 用本地 deterministic runtime 初始化 run、生成 node plan、切分 context、记录 node result、推进状态和 replay。
- 从 skill JSON specs 渲染 standalone HTML runtime diagram。

## 目标

目标是让 skill 行为可解释、可验证、可恢复、可复用：

- 生命周期由 `skill.machine.json` 表达。
- state 内部工作由 `node.graph.json` 表达。
- node 内部步骤由 `contracts/nodes.json` 表达。
- 约束由 `rules/` 表达。
- 上下文加载由 `context-policy.json` 表达。
- 运行状态由 `scripts/skill_runtime.py` 控制。
- 行为期望由 `evals/` 压力场景表达。

## 设计哲学

- **Theory first**：先定义目的、领域模型、不变量、失败模式和判断标准，再写执行流程。
- **State machine outside, DAG inside**：状态机管理生命周期，DAG 管理 state 内部依赖。
- **Sequential nodes**：每个 node 是有序 micro-workflow，步骤必须可报告、可校验。
- **Rules are first-class**：硬约束放在 `rules/`，不藏在参考材料里。
- **Progressive context**：runtime 按 active state、node、step 切分上下文。
- **Deterministic runtime**：本地脚本负责计划、状态、事件、结果接收和 replay。
- **Behavior evals**：用压力场景测试行为，而不是只检查文件是否存在。

## 怎么用

把本仓库目录放到 agent runtime 会扫描的 skills root 下，然后像普通 skill 一样调用 `skill-framework`。

示例 prompt：

```text
Use skill-framework to create a new skill for API documentation workflows.
Use skill-framework to upgrade this existing skill into the canonical workflow-program structure.
Use skill-framework to validate this skill's machine, graph, contracts, rules, runtime, and evals.
Generate a standalone HTML runtime diagram for this skill.
```

也可以直接运行脚本：

```bash
python scripts/init_skill.py my-skill --path /tmp/skills
python scripts/validate_skill.py .
python scripts/run_skill_evals.py .
node scripts/render_skill_html.mjs . -o skill-flow.html
```

runtime 操作从初始化 run 开始：

```bash
python scripts/skill_runtime.py init-run <target-skill-path>
```

后续由 runtime 返回 `user_update` 和 `agent_next_action`，agent 先转发 `user_update.message`，再执行 `agent_next_action.command`。

## 更多文档

维护者指南、文件语义、共享 context loading 模型、编辑路径、测试方法和反模式见 [CONTRIBUTE.md](CONTRIBUTE.md)。
