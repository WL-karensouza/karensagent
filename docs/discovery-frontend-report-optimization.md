# Discovery Plan: 投研报告前端展示优化

**Date**: 2026-07-15
**Product Stage**: existing
**Discovery Question**: 如何将投研报告从一段 Markdown 纯文本变成结构清晰、重点突出、视觉美观的分析报告？

---

## Ideas Explored

10 个方案来自 PM/Designer/Engineer 三视角头脑风暴，最终选定 3 个：

| # | 方案 | 选定 |
|---|------|------|
| 1 | 分层摘要卡片 | - |
| 2 | 报告书签导航 | - |
| 3 | 报告收藏 & 对比 | - |
| **4** | **评分可视化**（环形仪表盘 + 彩色徽章） | ✅ |
| 5 | 关键数据迷你图表 | - |
| **6** | **操作建议卡片突出** | ✅ |
| **7** | **组件化报告渲染**（替代 v-html） | ✅ |
| 8 | 对话式追问 | - |
| 9 | 渐进式加载 | - |
| 10 | 报告分享卡片 | - |

---

## Selected Ideas for Validation

### 方案 7: 组件化报告渲染（基础，先做）

**目标**：废弃当前的 `v-html` 渲染，改为由 Vue 组件驱动的结构化报告。

**组件清单（基于 E1 真实 JSON 结构验证）**：

```
StockReport.vue（报告容器，废弃 v-html）
├── ScoreGauge.vue            — SVG 环形仪表盘（方案4）
├── DecisionBadge.vue         — 看多/震荡/看空 徽章（方案4）
├── SummaryCard.vue           — 综合评估段落
├── DimensionSection.vue ×5   — 5 维分析卡片（中文 key，每维形状不同）
│   ├── 技术面       {signal, insight}
│   ├── 消息面       {sentiment, insight}
│   ├── 基本面及财务分析  {signal, insight(400+字)}
│   ├── 风险面       {level, top_risks[], insight}
│   └── 市场环境     {style_match, insight}
├── RiskWarningList.vue       — 散户注意事项 (risks[])
├── CatalystList.vue          — 利好催化 (catalysts[])
├── WatchPointList.vue        — 关键观察点 (watch_points[])
├── HoldingAdviceCard.vue     — 持仓建议双栏 + 狙击点位（方案6）
│   ├── no_position / has_position 两种模式
│   └── sniper_points {ideal_range, stop_loss, take_profit}
├── SignalAttribution.vue     — 信号归因权重表 (signal_attribution[])
└── ReportMeta.vue            — Token 用量 + 生成时间
```

**关键发现（E1 实验）**：
- sections 使用**中文 key**（技术面/消息面/基本面及财务分析/风险面/市场环境），不是英文
- 每个 section 的**内部形状不同**——DimensionSection 需根据 key 动态适配
- `position_advice` 含两个子对象 `{no_position, has_position}`，非短/中/长期
- 所有字段 100% 出现，JSON 结构足够稳定驱动组件化 ✅

### 方案 4: 评分可视化

**目标**：用视觉元素替代纯数字，让用户半秒内感知评分高低。

- 环形进度条（SVG）：0-100 分，红→黄→绿渐变
- 多空徽章：绿色"看多"、黄色"震荡"、红色"看空"
- 各维度信号图标（📈📉📊）微件阵列

### 方案 6: 操作建议卡片突出

**目标**：把持仓建议和关键价位做成报告中最显眼的卡片。

- 差异化背景色（浅蓝底 + 金色边框）
- 三列布局：短期建议 / 中期建议 / 长期建议
- 狙击点位：理想买入区间 / 止损价 / 止盈价
- 无持仓 vs 有持仓 两种展示模式

---

## Critical Assumptions

| # | Assumption | Category | Impact | Uncertainty | Priority |
|---|-----------|----------|--------|-------------|----------|
| C2 | `report_json` 结构稳定且字段完整，能驱动组件渲染 | Feasibility | 🔴 高 | 🔴 高 | P0 |
| B2 | `sniper_points` / `position_advice` 字段数据质量可靠 | Feasibility | 🔴 高 | 🔴 高 | P0 |
| A2 | `score` 分布足够分散（不集中在 50-70），仪表盘有区分度 | Feasibility | 🟡 中 | 🟡 中 | P1 |
| A5 | `decision` / `score` 字段在每份报告中可靠存在 | Feasibility | 🟡 中 | 🟡 中 | P1 |
| C5 | 十大维度每个都有独立渲染价值，用户会逐维度阅读 | Value | 🟡 中 | 🟡 中 | P1 |
| B1 | 操作建议是用户最高频阅读目标 | Value | 🟢 中 | 🟢 低 | P2 |
| A1 | 色彩编码比纯数字更直观 | Usability | 🟢 中 | 🟢 低 | P2 |
| C1 | 组件化 vs v-html 有明显的体验提升 | Value | 🟢 中 | 🟢 低 | P2 |
| B4 | 新增颜色与现有 `#F1EFEA` 暖白 + `#D97706` 橙色配色协调 | Usability | ⚪ 低 | ⚪ 低 | P3 |
| C4 | 组件化渲染性能不会比 v-html 差 | Feasibility | ⚪ 低 | ⚪ 低 | P3 |

---

## Validation Experiments

| # | Tests Assumption | Method | Success Criteria | Effort | Timeline |
|---|-----------------|--------|-----------------|--------|----------|
| E1 | C2 / B2 / A2 / A5 | 3只不同类型股票走完整管道，统计 JSON 字段完整度 | score+decision 100%，sniper_points ≥80%，6+ sections 有内容 | 20 min | Day 1 |
| E2 | C5 / 组件划分合理性 | 用一份真实 JSON 写静态组件原型，验证组件划分是否合理 | 组件树覆盖 JSON 所有字段，无信息丢失 | 2 hr | Day 1-2 |
| E3 | A1 / B1 / C1 | A/B 对比：静态原型 vs 现有 v-html 报告页，主观偏好投票 | ≥3/5 人偏好新版 | 30 min | Day 2 |

---

## Experiment Details

### E1: JSON 字段完整度抽样 ✅ 已完成

**结果**: P0 假设全部通过。

| 字段 | 出现率 | 状态 |
|------|--------|------|
| score | 100% (2/2) | ✅ |
| decision | 100% (2/2) | ✅ |
| summary | 100%，242字 | ✅ |
| sections | 100%，5 个中文键 | ✅ |
| risks | 100%，2-3条 | ✅ |
| catalysts | 100% | ✅ |
| sniper_points | 100%，3个完整子键 | ✅ |
| position_advice | 100%，no_position/has_position | ✅ |
| watch_points | 100% | ✅ |
| signal_attribution | 100% | ✅ |

**发现的问题**:
1. 3/10 iFinD 维度始终失败：实时行情、近期新闻、公司公告 — 需排查 SKILL 权限
2. 300750 JSON 解析崩溃 → **已修复**：`_parse_json()` 容错解析器（尾随逗号+截断补全+提取）
3. 工作树数据库未初始化 — `report_id` 返回 null
| sections (6 个) | 100% | ≥80% |
| sniper_points | ≥80% | ≥60% |
| position_advice | ≥80% | ≥60% |
| risks | 100% | ≥60% |
| catalysts | 100% | ≥50% |

**Decision**: 若 P0 字段 < 100%，需要先加固后端 Prompt 和 JSON Schema，再写前端。

### E2: 静态组件原型

**Hypothesis**: 当前 6 维 sections + summary + risks + catalysts 的结构可以合理划分为 15 个左右 Vue 组件。

**Setup**:
- 取 E1 中质量最好的一份 report_json
- 在 `StockReport.vue` 旁边新建 `components/report/` 目录
- 写静态组件（不接动态数据，用 props 传入）

**组件树验证清单**:
- [ ] ReportHeader — 股票代码 + 时间
- [ ] ScoreGauge — SVG 环形进度条 + 渐变
- [ ] DecisionBadge — 看多/震荡/看空
- [ ] SummaryCard — 一段文字摘要
- [ ] DimensionSection（复用 6 次）— 可折叠分析卡片
- [ ] HoldingAdviceCard — 短中长期建议
- [ ] RiskWarningList — 风险列表
- [ ] CatalystList — 催化剂列表
- [ ] ReportMeta — Token + 时间

**Decision**: 若组件划分覆盖所有 JSON 字段且无冗余，进入实现阶段。

### E3: A/B 主观对比

**Hypothesis**: 组件化报告比 v-html 更易读。

**Setup**:
- 同一份报告同时渲染为两页（不同路由或 tab）
- 找 3-5 人快速浏览并给出偏好
- 收集定性反馈（哪个部分好、哪个部分可以改进）

**Decision**: 若 ≥60% 偏好新版，推进实现。

---

## Discovery Timeline

```
Day 1 (Jul 15):
├── E1: 5只股票抽样验证 JSON 结构稳定性
├── 修复 E1 发现的后端字段缺失问题（如有）
└── 确定最终组件树

Day 2 (Jul 16):
├── E2: 写静态组件原型
├── 确定配色方案（环形图渐变 + 建议卡片背景色）
└── E3: A/B 对比验证

Day 3 (Jul 17):
├── 组件开发（按组件树逐个实现）
├── 替换 StockReport.vue 的 v-html 部分
└── 适配 StockDashboard.vue 的 SSE 报告预览卡片

Day 4 (Jul 18):
├── 评分可视化（方案4）— ScoreGauge + DecisionBadge
├── 操作建议卡片（方案6）— HoldingAdviceCard
└── 集成测试 + 边界情况处理
```

---

## Decision Framework

- **若 E1 JSON 稳定性 < 阈值** → 先加固后端 `analyze.py` 的 Prompt 和 JSON Schema，等 JSON 稳定后再组件化
- **若 E2 组件划分不合理** → 调整组件树，合并冗余组件，拆分过大的组件
- **若 E3 A/B 对比新版不被偏好** → 收集具体原因，针对性修改后再次对比
- **全部通过** → 按 Timeline 推进开发

---

## Out of Scope (本次不做)

- ❌ Prompt 优化（用户明确要求延后，另开 Discovery 或直接动手）
- ❌ 对话式追问（方案 8）
- ❌ 报告对比功能（方案 3）
- ❌ 迷你图表/ECharts（方案 5）
- ❌ 报告分享卡片（方案 10）
- ❌ 渐进式 SSE 流式渲染（方案 9）

---

## Next Steps

1. **立即执行 E1**：5 只股票 JSON 字段完整度抽样
2. Prompt 优化（用户另开）：将 6 维 Skills 输出格式改为 iFinD 十大模块 + 短中长期建议
3. 组件开发完成后，可考虑 `/design-sync` 将组件库同步到 Claude Design
