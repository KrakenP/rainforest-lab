# Rainforest Lab

[English](README.md)

Rainforest Lab 是一个面向 AI agent 的、由种子和天气系统驱动的研究框架。

v0.1 版本采用 skill-first 设计：仓库的核心产物是 `skills/rainforest-lab/`，这是一个可供 Claude、Codex 以及类似 coding agent 复用的 Agent Skill。

## 安装

把 skill 目录复制到你的 agent skill 目录：

```text
skills/rainforest-lab/
```

Claude 项目安装：

```text
.claude/skills/rainforest-lab/
```

Codex 安装：

```text
.codex/skills/rainforest-lab/
```

## 核心循环

```text
Forest Grounding
-> Tree and Seed Modeling
-> Research Work
-> Continuous Seed Capture
-> Seed Scoring and Ranking
-> Weather Routing
-> Sowing
-> Nursery Validation
-> Research Task Planning
-> Result Classification
-> Archive Update
```

中文理解：

```text
森林定基
-> 建立研究树和种子
-> 执行研究工作
-> 持续捕获新种子
-> 评价并排序种子
-> 用天气系统分配注意力
-> 播种高优先级种子
-> 在苗圃中低成本验证
-> 生成下一轮研究任务
-> 分类研究结果
-> 更新归档记忆
```

## 多 agent 协作 (v2.0)

v2.0 把每个 cycle 的单程 role 流水线升级成 **gardener↔skeptic 有界研讨循环 + 并行竞争 gardener + 不同模型族的对抗性 skeptic**。coordinator 仍是 forest state 的唯一写者，按 `tree_id` 排序确定性合并 per-tree 结果，因此整个 cycle 是可复现的。

刚性纪律（有测试守卫）：

- 被辩过的 `stub_result` 仍不能变 fruit。
- skeptic 对全 hard gate 通过的 fruit-candidate 投 `reject` **不能否决** —— pre-G7 第二次挑战只记录、不改 gate 结果。
- skeptic 适配器在自己的模型族与 gardener 相同时**结构性拒跑**（反 LLM 自偏）。
- 无 silent fallback：skeptic / LLM 不可用即 hard fail。
- `max_debate_rounds = 0` + 单 gardener 等价 v1 单程循环。

完整角色阵容、研讨循环、有界辩论规则、只记录不否决的第二次挑战、以及新的事件类型 (`gardener_parallel_dispatch`, `debate_round`, `skeptic_challenge`)，见 `skills/rainforest-lab/references/multi-agent-collaboration.md`。

## 执行诚实性

Rainforest 允许 agent 执行研究任务，但每个任务必须声明一种执行模式：

- `plan_only`：只做计划，不产生证据。
- `manual_result`：结果由用户提供。
- `stub_result`：模拟或演示结果。
- `tool_executed`：agent 真实使用工具、代码、数据或浏览器完成验证。

模拟结果不能被描述成真实证据。

## 核心隐喻

- `Forest`：完整研究状态。
- `Tree`：已经成形、正在投入的研究方向。
- `Seed`：潜在新方向。
- `Weather`：注意力和研究预算调度系统。
- `Nursery`：种子的低成本验证层。
- `Fruit`：有研究价值的正向结果。
- `Golden Leaf`：有价值的失败。
- `Sick Leaf`：泄漏、未来函数、伪相关或不可复用的危险结果。

Rainforest 的目标不是替 agent 得出夸张结论，而是帮助 agent 更好地决定下一步研究哪里、何时停止过度深挖、如何保存失败经验，以及如何从研究过程中生成新的高潜力方向。

## 许可证

MIT License。详见 [LICENSE](LICENSE)。
