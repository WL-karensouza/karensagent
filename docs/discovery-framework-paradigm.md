# Discovery Plan：stockAgent 框架与提示词范式借鉴

**日期**：2026-08-01
**产品阶段**：存量产品（stockAgent 生产运行中）
**发现议题**：`D:\Hello-Agent` 中三个 Agent 框架（CAMEL / LangGraph / transformer）与三个提示词范式（Plan&Solve / ReAct / Reflection），哪些值得 stockAgent 借鉴
**决策目标**：产出"引入 / 暂不引入 / 实验后再定"清单，及每条结论的验证实验

---

## 1. 现状与能力缺口

当前管线（代码实证）：

```
SKILL 10 维度采集（skill/report.py：SSE 流 + 同步双轨，维度级 try/except 降级，
  critical 维度失败 → has_critical_failure 硬终止）
→ analyze()：deepseek-v4-flash 单次调用，三层 system prompt，thinking 模式，
  _parse_json 三策略语法容错（尾随逗号 / 截断补全 / 最外层提取）
→ render_markdown → push_to_feishu
```

| # | 能力缺口 | 代码证据 |
|---|---|---|
| G1 | 无输出**语义**校验：schema 要求 signal_attribution 权重和=1.0、风险≥2 催化≥2，生产路径只做 JSON 语法容错，语义规则全靠 LLM 自觉 | `analyze.py:_parse_json` 仅语法层；语义检查逻辑已存在于 `tests/e1_field_completeness.py`（check_field/check_module）但未接入生产 |
| G2 | 无质量重试：`finish_reason=length` 截断只打日志，截断 JSON 经补全策略照用，后段模块（8/9）可能内容残缺 | `analyze.py` 87-88 行诊断日志 |
| G3 | 9 模块巨型 prompt 单次生成，max_tokens=16384 一把出，长输出后段质量稀释 | `analyze.py:80`、`prompts/output_schema.py` |
| G4 | 无历史记忆：报告永远是孤立快照，说不出"较上次…"；DB 已存 report_json 但分析时从不消费 | `models.py:37` 存、`stock_api.py:440` 写，无读回注入 |
| G5 | 采集串行：10 维度 for 循环 + sleep 限速，失败只有"硬终止 / 塞 ⚠️ 文本"两档 | `skill/report.py` sync/stream 两版 |
| G6 | 分析视角单一：通才 analyst 单次采样，多空判断无对抗校验 | `analyze()` 单次 chat.completions |

## 2. 对象全景（七个）

| 对象 | 本质 | 核心机制 | 仓库示例成熟度 |
|---|---|---|---|
| CAMEL | 角色扮演多智能体 | RolePlaying 双 Agent 对话循环 + Workforce 任务编排 + 冲突协商状态机 + User 侧终止裁决 | 协商机制用心，但正则判意图脆弱、两文件逻辑重复 |
| LangGraph | 图状态工作流 | StateGraph 节点 + TypedDict 状态 + add_messages reducer + checkpoint | 仅线性三节点示例；conditional_edge / HITL 均未演示 |
| transformer | 原理教学 | 从零手写 attention / encoder / decoder + decoder-only 论证 | 纯教学零应用代码；价值是心智模型（注意力 O(n²)、长上下文稀释） |
| Plan&Solve | 单轮增强范式 | Planner 出步骤清单 → Executor 逐步执行、历史累积；开环 | 1+N 次调用；计划错了错误沿链放大、中途不可改 |
| ReAct | 工具循环范式 | Thought/Action/Observation 循环 + 工具注册表，5 步兜底 | 格式解析脆弱；适合事实查询 |
| Reflection | 自我批判范式 | 生成→评审→重写闭环，三角色模板 + Memory 轨迹 + "无需改进"早停 | 每轮 3 次调用；弱模型易"自我表扬"早停 |

**关键观察**：三个范式都是"prompt 模板 + Python 控制流"，零框架依赖——借鉴范式不必引入任何框架。

## 3. 候选方向与评估结论

| # | 方向 | 来源 | 对应缺口 | 结论 |
|---|---|---|---|---|
| 1 | Schema 语义验证器（纯 Python 校验层） | 范式规则显式化思路 + 复用 e1_field_completeness | G1 | ✅ 深入验证→倾向直接建设 |
| 2 | Reflection 质量自检（评审员二次调用） | Reflection 范式 | G1+G2 | ❌ **已砍（2026-08-01）**：评审员橡皮图章化——早停率 100%、10 股发现问题 0 个、重写 0 次（A2 证伪）；附加 token 均值 +63.5% 远超 40% 门槛（A3 未过）；两版零差异无盲评价值 |
| 3 | ReAct 式数据自愈 | ReAct 范式 | G5 | ❌ 暂不引入：东财 fallback 已存在、SKILL 工具集固定，增量价值低 |
| 4 | LangGraph 重构采集层 | LangGraph 框架 | G5 | ❌ 暂不引入：SSE 双轨稳定，asyncio.gather 并行可解八成，换框架是大重构 |
| 5 | 历史对比记忆（奇数位采样注入） | LangGraph checkpoint / CAMEL Memory 思路 | G4 | ✅ **已引入（2026-08-01）**：A5 客观通过（prompt 增量 +0.9%~3.2% ≪ 30%）；A4 用户直接确认价值，免盲评。实现见 stock_agent/history.py，4 个生产调用点已接入 |
| 6 | Plan&Solve 模块化生成 | Plan&Solve 范式 | G3 | ✅ 深入验证（token 成本需实测） |
| 7 | 流程阶段可视化（"评审中"SSE 阶段） | LangGraph 节点思路 | — | 依附于方向 2，非独立方向 |
| 8 | CAMEL 多空辩论（牛×熊×首席） | CAMEL 框架 | G6 | ⚠️ 深入验证但带 kill gate（成本 3~5 倍） |
| 9 | HITL 推送确认 | LangGraph HITL | — | ❌ 暂不引入：前端已有手动推送按钮 |
| 10 | decoder-only 心智模型内训 | transformer 仓库 | — | 非代码借鉴：作为方向 6 的决策依据与团队内训材料 |

## 4. 关键假设清单（Impact × Uncertainty）

| # | 假设 | 类别 | 方向 | Impact | Uncertainty | 优先级 |
|---|---|---|---|---|---|---|
| A1 | schema 硬规则（权重和/必填/枚举/score-decision 一致性）可穷举为程序断言 | 可行性 | 1 | 高 | **低**（e1_field_completeness 已验证可行） | P1 直接建 |
| A2 | LLM 评审员能抓住验证器抓不到的语义问题（罗列数据不解读 / 术语堆砌 / 事实推断未区分），且非"自我表扬"式早停 | 价值 | 2 | 高 | 中 | P2 |
| A3 | Reflection 常态附加成本可控：评审早停率 ≥70%（多数报告仅 +1 次调用） | 商业可行 | 2 | 中 | 中 | P2 随 A2 测 |
| A4 | "vs 上次"对比显著提升报告感知价值（评分/结论/风险变化一目了然） | 价值 | 5 | 高（用户指定） | 中 | **P1** |
| A5 | 奇数位采样 + 骨架注入（非全文）使 prompt 长度增量 ≤+30% | 可行性 | 5 | 中 | 低 | P1 随 A4 测 |
| A6 | 模块化生成消除 finish_reason=length 截断，后段模块（8/9）质量提升 | 价值 | 6 | 高 | 中 | P3 |
| A7 | 模块化总 token ≤ 单次生成的 1.8 倍（每模块重复携带数据+骨架的代价） | 商业可行 | 6 | 高 | **高** | P3 随 A6 测 |
| A8 | 多空辩论改善 signal_attribution 平衡性与 decision 准确性 | 价值 | 8 | 未知 | 高 | P4（kill gate） |
| A9 | 3~5 倍 token 成本换来的质量提升值得 | 商业可行 | 8 | 未知 | 高 | P4 依赖 A8 |

**leap-of-faith 假设**：A7（模块化成本）与 A8（辩论价值）——不确定性最高、决定两条线生死。

## 5. 用户四问澄清（已确认共识）

### Q1：质量线 1+2 具体如何提高质量？

两者分工互补，不是二选一：

**方向 1 = 廉价的守门员（结构硬校验，零 LLM 成本）**
analyze 产出 dict 后，跑一层纯 Python 断言：
- signal_attribution 权重和 = 1.0（±0.05 浮点容差）
- decision ∈ {看多, 震荡, 看空}，score ∈ [0, 100]
- module_8.risks ≥ 2 条，module_7.positive / negative 各 ≥ 1 条
- 一致性：score ≥ 60 却 decision=看空 → 矛盾
- 9 个模块 key 齐全

抓到违规 → 把**具体违规清单**回传 LLM 定点修正，或直接拒绝重试。
重要发现：`tests/e1_field_completeness.py` 已有 check_field / check_module / signal_attribution 检查逻辑——方向 1 本质是把这套已验证的检查**从 tests 下沉到生产管线**，不是从零发明。

**方向 2 = 昂贵的主编（语义软校验，+1~2 次调用）**
验证器抓不到"质量差但格式对"的报告，例如：
- 违反 core_rules 第 7 条"说人话"：罗列数据不给逻辑解读
- 违反第 4 条：术语堆砌（"戴维斯双击"无白话解释）
- 违反第 2 条："数据显示"与"分析认为"未区分

这些正则/断言无解，只能 LLM 评审。做法（借 Reflection 范式）：analyze 产出后，"严苛评审员"输入 = 原始数据报告 + 产出 JSON + 八条原则清单，输出 = 问题清单或"通过"；有问题则携带问题清单二轮重写违规模块；评审说"无需改进"即早停。

**组合效果**：1 先筛掉硬错误（避免浪费评审员调用），2 再提语义质量；常态成本仅 +1 次调用。

### Q2：历史报告采样规则（用户确认需求，高优先级）

按时间倒序（最新 = 第 1 份）：

| 历史报告数 N | 取用序号 | 份数 |
|---|---|---|
| 0 | — | 0（不注入） |
| 1 | [1] | 1 |
| 2 | [1, 2] | 2 |
| 3~4 | [1, 3] | 2 |
| 5 | [1, 3, 5] | 3 |
| ≥6 | [1, 3, 5, 7, 9] | 5（封顶） |

策略含义：近期密集、远期稀疏，兼顾短期变化与中期趋势。
备注（仅记录不修改规则）：N=2→N=3 时采样密度存在一个跳变（连续→隔位），系用户明确规则，照此执行。

配套设计（控制成本）：
- **数据源**：DB 报告表 `report_json` 字段（`models.py:37` 存、`stock_api.py` 写），不用 reports/ 下的 CLI 产物 md
- **注入形态**：每份历史只提取骨架（score / decision / rating_sentence / core_logic / signal_attribution），非全文；5 份骨架 ≈ 1~2k tokens
- 注入位置见 Q3

### Q3：Plan&Solve 在哪个环节触发？

触发点 = **采集完成之后、正式生成之前**（替换现在的单次 analyze 调用）。历史报告是"材料"不是"触发点"：

```
采集完成（data_md + sections）
  ↓
载入历史骨架（方向 5：按 Q2 规则从 DB 取）
  ↓
Planner 调用：输入 = 数据报告 + 历史骨架 → 输出 = 核心结论骨架
  （score 区间预判 / decision 方向 / 3 条核心逻辑 / 主要风险与催化）
  ↓
Executor：module_2~9 携带「数据 + 骨架 + 历史」分模块生成（可并行）
  ↓
汇总 → 验证器（方向 1）→ 评审员（方向 2，可选）
```

方向 5 与 6 正交：**5 决定输入里放什么材料，6 决定分几次、按什么顺序生成**，互不冲突、天然叠加。

### Q4：CAMEL 辩论在哪个区间触发？与方向 6 冲突吗？

触发区间同样是"生成环节"，因此与 6 在实现层面**互斥**——两者都在重构生成流程：
- 6 = 单角色多步骤（规划者 + 逐模块执行者）
- 8 = 多角色同目标（牛派 × 熊派 × 首席整合）
- 叠加 = 组合爆炸（规划 + 每模块 × 多空辩论 → 20+ 次调用），不推荐

可组合但昂贵的形态：辩论只发生在"结论层"（score / decision / signal_attribution 的多空对抗），模块化负责"内容层"（各模块 prose）。

**处理方式**：6 与 8 作为生成环节的**两条备选路线**并行实验、A/B 择优；方向 8 带 kill gate——仅当方向 2+6 验证有效且质量天花板仍不足时，才执行方向 8 的实验。

## 6. 验证实验

验证集：复用 `analyze.py` DEFAULT_WATCHLIST 扩展至 10 只（覆盖大/中/小盘、港股各 1）。

| # | 验证假设 | 方法 | 成功判据 | 成本 | 时间 |
|---|---|---|---|---|---|
| E0 | A1 | 将 e1_field_completeness 检查下沉为 `validate_report()`，接入 analyze 管线 + 单测覆盖每条规则 | 单测全绿；对历史报告回放能标出已知瑕疵 | ~0.5 天 | Week 1 |
| E1 | A4 / A5 | 历史对比原型：按 Q2 采样 + 骨架注入，选 3 只 DB 内 ≥3 份历史的股票，各生成"有/无历史"两版，用户盲评；同时统计 prompt 长度增量 | 盲评偏好"有历史"版 ≥ 2/3；长度增量 ≤+30% | ~1 天 + 盲评 | Week 1 |
| E2 | A2 / A3 | Reflection 原型：10 只验证集，单次 vs +评审员，人工盲评 + 统计早停率/附加 token | 盲评可感知改善；早停率 ≥70%；附加 token ≤+40% | ~2 天 | Week 2 |
| E3 | A6 / A7 | 模块化原型：同 10 只，先 plan 后模块并行，统计 finish_reason=length 比例、总 token、后段模块盲评 | 截断率 → ~0；总 token ≤1.8×；模块 8/9 盲评不劣化 | ~2 天 | Week 2 |
| E4 | A8 / A9 | 辩论原型：选 5 只历史结论明显一边倒的股票，牛/熊/首席三角色，人工评平衡性 + 成本统计 | 平衡性评分显著优于单次 **且** 单次成本 ≤4× | ~2 天 | Week 3（kill gate 后） |

## 7. 时间线与决策框架

**Week 1**：E0 直接建设上线（后续实验的客观度量基础）；E1 原型 + 盲评（用户指定优先级）
**Week 2**：E2 / E3 并行（共用 10 只验证集与盲评流程）
**Week 3**：汇总结论；E4 跑或 kill；产出最终引入清单

决策门槛：

| 方向 | 门槛 |
|---|---|
| 1 验证器 | 无门槛，直接建 → **已建设上线（E0，2026-08-01）** |
| 5 历史对比 | E1 盲评偏好率 ≥ 2/3 → 引入 → **已引入：A5 客观通过；A4 用户拍板（2026-08-01）** |
| 2 Reflection | 早停率 ≥70% 且盲评可见改善 → 引入 → **已砍：早停率 100% 但发现问题 0 个（自我表扬），附加 token +63.5%，零收益高成本（2026-08-01）** |
| 6 模块化 | 截断率 → ~0 且 token ≤1.8× → 引入；否则回退单次生成 |
| 8 辩论 | E2+E3 落地后质量天花板仍不足 **且** E4 平衡性显著提升 → 引入；否则 kill |

## 8. 暂不引入方向归档

| # | 方向 | 理由 |
|---|---|---|
| 3 | ReAct 数据自愈 | 东财 fallback 已在 `_enrich_performance` 落地；SKILL 工具集固定，LLM 决策换工具无施展空间 |
| 4 | LangGraph 重构采集层 | SSE/sync 双轨稳定运行；G5 的核心痛点（串行）用 asyncio.gather 并行化即可解八成，引入图框架的重构成本与收益不成比例 |
| 9 | HITL 推送确认 | 前端 StockReport.vue 已有手动推送入口（handlePush），增量价值低 |
| 10 | transformer 代码借鉴 | 纯原理教学，无应用代码；正确用法是作为方向 6（长上下文稀释论证）的决策依据与团队内训材料，不做代码迁移 |

## 9. 下一步可选动作

- 为 E0（验证器）直接出实现方案（不需要实验，属建设项）
- 为 E1（历史对比）写实现 plan：DB 读取 + 骨架提取 + 采样器 + prompt 注入点
- 设计盲评打分表（E1/E2/E3 共用，保证结论可比）
