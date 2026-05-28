# 🌳 Rainforest Lab

> **多 agent 诚实研究，纪律由结构保证。**
> 种下一个研究方向 → 长成一座假设森林 → 只有过了每一道 gate 的才算证据。

[English](README.md) · License: MIT · 状态：`skill` ✅ · `python package` 🚧 · `mcp server` 📅

Rainforest Lab 是一个**市场不可知的研究框架**，为 AI agent 而生。它把开放式研究当成一座"方向的森林"——里面有种子、天气、金叶、对抗性 skeptic，还有 LLM 无法靠口才蒙混过去的 gate。

整个东西围绕一个固执的想法构建：**"此处无 alpha" 是一个合法的科学结论**；一个允许 LLM 自行宣告胜利、无人核验的框架——那是 bug，不是 feature。

---

## 🌱 这玩意儿要长成什么样

```text
你：    "我想研究 A 股银行股盈利差对下个月超额收益的预测能力。"

Claude: [确认方向 · 问 3 个澄清问题]
        [调 rainforest-lab MCP] → 给出 blueprint 蓝图
        [用户审阅 + 微调："字段加上 P/B"]
        [在用户批准下把 5 个文件写进项目目录]
        [带用户配 LLM：gardener 用哪家？skeptic 用哪家？—— 必须不同模型族]
        "准备好了。要开跑吗？（目标 5 fruit，最多 4 小时）"

你：    "开。"

[Cycle 1 → 评估 3 个候选 → 0 fruit, 2 golden_leaf, 1 dead.   ← 诚实汇报]
[Cycle 2 → ...]
```

不用手写一行代码。不喊"魔法 alpha"。就是一个能自跑、可证伪的研究——**用户只管方向**，管道由框架兜。

---

## 📦 三根支柱

| 支柱 | 是什么 | 状态 |
|---|---|---|
| 📚 **Skill** — `skills/rainforest-lab/` | 方法论 + 模板：森林定基、天气、种子、苗圃、分类、归档记忆、多 agent 协作 (v2.0) | ✅ 已发布 |
| 🛠️ **Python 包** — `python/rainforest_lab/` | 市场不可知引擎：state · validate · cycle · deliberation · trajectories · DSL kit · gates kit · LLM Protocols + LiteLLM 参考适配 | 🚧 v0.1.0 进行中 |
| 🔌 **MCP Server** — `mcp/` | 产品面：blueprint 蓝图生成 + 脚手架 + LLM 配置 validator + 通过 MCP sampling 驱动引擎 | 📅 v0.2.0（产品发布版） |

skill 教方法论。包做实现。MCP server 把这两层包装成"用户可以直接对话"的产品。

---

## 🌧️ 🌳 🍎 隐喻系统（不是好看，是有用）

| 符号 | 概念 | 干什么 |
|---|---|---|
| 🌳 **Tree** | 一个正在投入的研究方向 | 有 branches（假设谱系）、预算份额、天气先验 |
| 🌱 **Seed** | 一个潜在的新方向 | 播种前在 10 个维度打分 |
| ☀️🌧️🌪️ **Weather** | 每个 cycle 的注意力路由器 | 13 种天气——heavy_rain · rain · drizzle · drought · heatwave · frost · thunderstorm · fog · wind · spring · monsoon · flood · wildfire |
| 🌿 **Nursery** | 进 gate 前的低成本验证 | 7 项有界检查，避开浪费昂贵的 evaluation |
| 🍎 **Fruit** | 过了所有 hard gate + alignment 的因子 | PROMOTED（G7 ≥ 2）或 ENSEMBLE（G7 ≥ 1） |
| 🍃 **Golden Leaf** | 有价值的失败 | 边界信息可用，产 seed 留作日后复活 |
| 🟥 **Sick Leaf** | 中毒的结果（lookahead / leakage） | 永久禁止复用，warning 跨 cycle 留存 |

符号让整个循环**可审查**——每一步都有理由、都有能直接映射到代码的隐喻。

---

## 🤖 多 agent 研讨（v2.0）

单程 role 流水线会跑偏：一个模型自己想象、自己评判、自己对齐，最后把自己的意见当成"证据"出货。v2.0 把流水线换成 **gardener ↔ skeptic 有界研讨 + 并行竞争 gardener + 来自不同模型族的对抗 skeptic**。

- 🗣️ **Skeptic（红队批评者）**——必须用与 gardener **不同的模型族**（比如 gardener Kimi ↔ skeptic DeepSeek，或者 gardener OpenAI ↔ skeptic Anthropic）。模型族相同时 skeptic 适配器**结构性拒跑**。
- 🔁 **有界辩论**——`gardener 挖矿 → skeptic 挑刺（cull / revise / proceed）→ gardener 修订幸存者`，最多 `max_debate_rounds` 轮。然后才走 divergence → inspector → nursery → examiner 的剩余流水线。
- 🍎 **第二次挑战只记录、不否决**——pre-G7 阶段 skeptic 对 fruit-candidate 的挑战**不能**覆盖确定性 gate 的判决。对称于"被辩过的 stub 仍不能变 fruit"：**LLM 既不能造一个 fruit，也不能毙一个 gate 已经放行的 fruit**。
- 🌳🌳🌳 **并行 gardener**——一棵树一个 gardener，不同 temperature/style，按 `tree_id` 排序确定性合并保证可复现。

📖 完整规格：[`skills/rainforest-lab/references/multi-agent-collaboration.md`](skills/rainforest-lab/references/multi-agent-collaboration.md)。

---

## 🧬 轨迹进化（v2.1）

不是在一个 cycle 内进化因子字符串，而是**跨 cycle 进化整条推理路径**——借鉴近期文献里的轨迹级进化思路，套上 rainforest 的纪律壳。

- 🧬 **Mutate**——定位父代轨迹失败的那一步，冻结前缀，让 gardener 重写。
- ⛓️ **Crossover**——把 ≥ 2 个健康父代的高 reward 片段重组进子轨迹。
- 🛡️ **没有"血缘 fruit"**——子代一律 unclassified 起步，必须重过完整 gate battery。和 "LLM 不能把 stub 升级成 fruit" 对称，**也不能继承一个 fruit**。
- ☢️ **病父代有毒**——永远不被选去 mutate / crossover。lookahead 不会传染。

primitives 已发布；coordinator 整合可选。

---

## 🔒 纪律（真正的差异化）

大多数 "LLM 做 X" 的工作端出来一套漂亮工作流，报一个好看的数，没显著性检验，也没诚实失败。Rainforest 是从一次真实复盘出来的（**76 个"赢面" 被更严的 gate 砍到 1 个**），所以这个框架在结构上排斥这些事：

- 🚦 **Gate 完整性是类型不变量**——结果没有完整的 `GateRecord` + `execution_mode == tool_executed` 就**不能**被标 `fruit`。"76 pseudo-fruits" 这一类 bug 在结构上不可能发生，不是"靠纪律避免"。
- 📏 **Matched-random P99 显著性门槛**——G3 强制要求 OOS Sharpe > 同 regime mask 下 1000 个随机因子的 P99，阈值连同 provenance 一起冻结（`{date, N, universe, percentile}`）。
- 🤐 **无 silent fallback**——LLM 不可用就是 hard fail。合成结果伪装成真实结果，被当作 bug 不是 feature。
- ☝️ **单一可信源**——只有 canonical YAML state 被引擎读写，derived JSON 单向产生、永不回头吃。
- 🎯 **Sonnet-drivable 北极星**——护栏强到让一个较弱的模型也能驱动这个循环不漂移。先驱版本里**连 Opus 都跑偏过**。
- 📉 **0/N 是合法结果**——汇报"此处无 alpha" 是 feature 而不是 failure。可发表。

---

## ⚡ 快速开始

**今天（v0.1 skill 已发布）：**

```bash
# Claude
cp -r skills/rainforest-lab/ ~/.claude/skills/

# Codex
cp -r skills/rainforest-lab/ ~/.codex/skills/
```

然后跟你的 agent 说：

> *"用 rainforest-lab 帮我规划关于 [你的主题] 的研究。"*

agent 会读方法论、带你过 forest grounding、产出一份你可以亲自执行的 cycle 计划。

**即将到来（v0.1.0 Python 包 + v0.2.0 MCP server）：**

```bash
# Python 开发者路径——以代码驱动引擎
pip install rainforest-lab

# 终端用户路径——直接跟你的 host agent 说话（Claude Desktop / Cursor / ...）
claude mcp add rainforest-lab
```

⭐ Star 一下追踪 v0.1.0 / v0.2.0 发布进度。

---

## 🗺️ Roadmap

| 版本 | 范围 | 状态 |
|---|---|---|
| **v0.1 — skill** | 方法论规格 + 模板 + v2.0 多 agent 协作内容 | ✅ 已发布 |
| **v0.1.0 — engine** | `pip install rainforest-lab`：引擎 + LLM Protocols + LiteLLM 参考适配 + DSL kit + gates kit + trajectory primitives | 🚧 进行中 |
| **v0.2.0 — product** | MCP server：blueprint 生成 + 脚手架 + LLM 配置 validator + 用 sampling 取代文件系统 handoff | 📅 next |
| **v0.3+** | 办公室场景可视化（多 agent 协作变成可旁观的剧场）· 更多 blueprint 模板 · 下游 factor 合成层（ensemble） | 🔮 later |

---

## 🌱 参与贡献

Domain 插件、LLM 适配、blueprint 模板都是一等公民。

包发布后，写一个 domain 插件的路径应当是：

1. 挑一个 blueprint 模板（或者跟 MCP server 说话：*"我想在市场 Y 上研究 X"*）。
2. 用 `rainforest_lab.dsl` 注册你的字段和算子——parse / eval / 随机公式 / 复杂度推断都自带。
3. 用一份 YAML 给出 gates 阈值 profile——完整 gate battery 按你市场的参数化跑。
4. 实现 `ResearchDomain`——一般 ~150 行。
5. 发版。

刚性纪律不可谈；其他都开放。欢迎 PR 和 issue。

---

## 📜 许可证

MIT。详见 [LICENSE](LICENSE)。

---

> 这个框架从一次真实的 `76 pseudo-fruits → 1` 复盘里长出来。每一道 gate、每一场辩论、每一条不变量都不白存在——因为有人吃过亏才懂："LLM 宣告胜利"和"门真的过了"不是同一件事。🍃
