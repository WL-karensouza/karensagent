# 历史报告对比功能 · 发现与实施计划（E1 v2）

**日期**：2026-08-04
**产品阶段**：现有产品（单用户 dogfooding，使用者 = 需求方）
**发现议题**：历史报告如何对比、差异如何在投研报告展示、有历史时如何强制对比
**采样规则**：不变（N≤2 全取，N≥3 奇数位，封顶 5 份；见 discovery-framework-paradigm.md Q2）

---

## 一、探索过的想法（10 候选，三视角）

| # | 想法 | 结论 |
|---|------|------|
| 1 | 结构化对比字段 | ✅ 融入设计 D2 |
| 2 | 上次观点回测（报告后涨跌验证） | ❌ 本轮不做（工程重，后续议题） |
| 3 | 判断稳定性序列 | ❌ 被 D1 趋势图覆盖 |
| 4 | 强制对比规则 | ✅ 融入设计 D2 |
| 5 | 报告头变化横幅 | ❌ 用户未选，趋势图承担首屏对比 |
| 6 | 独立「历史对比」模块 | ❌ 用户指定放 module_9 顶部 |
| 7 | 信号归因 diff | ❌ 用户判定无实际意义 |
| 8 | 评分趋势折线图（ECharts） | ✅ 设计 D1 |
| 9 | 确定性计算+LLM 只写原因 | ❌ 用户选择 LLM 全量对比+机械校验兜底 |
| 10 | 校验器硬规则 | ✅ 融入设计 D2 |

## 二、用户确认的三项设计决策

1. **评分趋势图**：只认同候选 8。位置 = 报告页评分卡（score-card）右侧空白；X 轴报告时间、Y 轴分数；ECharts 按需注册仅 LineChart。
2. **强制对比、只述变化**：有历史必对比（机械保障）；只描述变化部分；无变化不强制描述（最终确认：渲染一行轻提示）。
3. **对比重点三块**：财务数据、股价涨跌、操作指南三要素（建仓/止损/止盈）；对比描述放 module_9 最前；三要素建议必须基于历史对比给出。

## 三、关键假设验证（讨论中已确认）

| 假设 | 结论 |
|------|------|
| 无变化时是否完全静默 | 否 → 渲染一行轻提示「与 YYYY-MM-DD 报告对比无重大变化」，让对比执行可见 |
| 「强制」靠提示词还是机械校验 | 机械校验：schema 字段 + validator 规则，缺失判违规触发定点修正 |
| 财务对比粒度 | module_3 key_indicators 精简注入（指标名+数值+趋势），对比落到数字 |

---

## 四、最终设计

### D1 评分趋势图（前端首屏）

- 新组件 `frontend/src/components/report/ScoreTrendChart.vue`
- 依赖：新装 `echarts`（用户指定 = 同意）；按需 `import { LineChart } from 'echarts/charts'`，不注册其他图表
- 嵌入 `StockReport.vue` score-card 右侧空白；浅色简约折线，匹配页面风格
- 数据：新接口 `GET /api/stock/reports/trend/{code}` → `[{created_at, score}]` **升序**，含当前报告点（复用 `database.get_recent_reports`）
- 数据点 < 2：不渲染图表，浅色文案「首次报告，无历史趋势」
- 当前报告点在数据里天然存在（报告先存库再展示）

### D2 强制对比机制（后端保障）

**schema 变更**（`module_9_操作指南` 内新增）：

```json
{
  "history_anchor": "2026-07-20",
  "history_compared": true,
  "changed_aspects": ["财务面", "股价面", "操作建议"],
  "history_changes": ["财务：营收增速 +12% → -3%，基本面转弱，建仓激进程度下调", "..."],
  "buy_strategy": "...（必须基于历史对比给出）"
}
```

- `history_anchor`：对比基准的最近历史报告日期（注入骨架里带时间，LLM 可填）
- `changed_aspects` 取值范围：财务面 / 股价面 / 操作建议；空数组 = 无变化（合法）
- `history_changes`：条目化描述（每条 = 变化点 + 对比日期 + 对建议的影响）

**validator 规则**（仅当注入历史时生效，`validate_report(report, has_history=False)` 加参）：

1. `has_history=True` → `history_compared` 必须为 true、`history_anchor` 非空，缺失 = 违规
2. `changed_aspects` 非空 ⇔ `history_changes` 非空（防只列方面不写描述，或反之）
3. 违规走现有定点修正流程（修正一轮；仍违规按现状附 `_validation_issues` 不阻塞——「强制」体现在必被检出+必触发修正）

**提示词变更**（`prompts/__init__.py`）：

- 删除旧指令（"在 module_1 核心逻辑中指出差异"，避免两处都写）
- 新指令：注入历史时必须逐项对比 财务/股价/操作建议 三块；建仓/止损/止盈必须基于历史同三要素对比后给出；变化写入 `history_changes`，无变化则 `changed_aspects` 置空

**骨架扩充**（`history.py extract_skeleton`）：

- 新增：`module_3.key_indicators` 精简（name+value+trend，约 4~6 行）、`module_4.trend` 一句、`module_9` 三要素（buy_strategy/stop_loss/take_profit）
- 顺带修复：现骨架提取了 `signal_attribution` 但从未注入的半死代码——本次直接移除该提取
- 存量历史报告自 2026-07-16 起即 9 模块结构，回溯兼容
- Token 增量约 +600~900/满 5 份，可接受

### D3 展示（双渲染路径同步）

- **前端** `HoldingAdviceCard.vue`：顶部渲染对比块（有 `history_changes` → 条目列表，标题带 `history_anchor` 日期；无 → 轻提示「与 {history_anchor} 报告对比无重大变化」）；其下才是建仓/止损/止盈
- **Markdown**（`render.py`，飞书推送/CLI 同享）：module_9 节顶部同规则渲染

### 无历史（N=0）时

不注入、不校验、module_9 无对比块、趋势图显示空态文案。

---

## 五、改动清单

**后端**（6 文件）：
1. `stock_agent/history.py` — 骨架扩充 + 注入渲染 + 移除 signal_attribution 死提取
2. `stock_agent/prompts/output_schema.py` — module_9 新增 4 字段
3. `stock_agent/prompts/__init__.py` — 指令句替换
4. `stock_agent/validator.py` — 新规则 + has_history 参数
5. `stock_agent/analyze.py` — has_history 传入 validate_report
6. `routers/stock_api.py` — 新增 `/reports/trend/{code}`

**前端**（4 处）：
7. 安装 echarts
8. 新组件 `ScoreTrendChart.vue`
9. `StockReport.vue` — score-card 嵌入趋势图
10. `HoldingAdviceCard.vue` — 顶部对比块 + 轻提示
11. `stores/stock.js` — fetchTrend

（render.py 归入后端第 6 项之外 → 实际后端 7 文件；计数以清单为准）

## 六、验证实验（验收用例）

1. **正例端到端**：挑 DB 中历史 ≥2 份的真实股票跑 `/skill-report/invest`，验收：趋势图升序含当前点；module_9 顶部对比描述与注入骨架一致（抽查数字）；建仓/止损/止盈体现对比调整
2. **机械校验负例**：构造 has_history=True 但缺字段报告 → validate_report 报违规
3. **无变化例**：结论相近时 `changed_aspects=[]` → 前端/Markdown 渲染轻提示行
4. **N=0 例**：新股票 → 无对比块、图表空态、不触发校验

## 七、执行顺序与决策框架

1. 后端链路（骨架→schema→提示词→校验→trend API）→ 单样本端到端（用例 1）通过后再动前端
2. 前端（echarts 组件→卡片嵌入→module_9 块）→ 四用例全过 → 交付
3. 若 LLM 对比准确率低（抽查数字不符）→ 回头调骨架信息量或提示词，不改展示层

**预估**：后端约 1 小时，前端约 40 分钟，验收约 20 分钟（含一次真实 LLM 调用）。

---

## 全局约束（所有任务适用）

- 注释一律中文；CSS 样式块顶部注释说明用途
- commit message 中文一句话（如 `fix(stock_agent): 历史对比骨架扩充`），不暴露 AI 写作痕迹
- 命名：Python snake_case；前端变量/函数 camelCase；Vue 组件与组件文件 PascalCase
- 局部修改纪律：不改任务清单之外的代码；不顺手重构
- 历史报告采样规则不变（`sample_history_indices` 不动）
- ECharts 按需引入：只注册 LineChart（Grid/Tooltip/CanvasRenderer 为折线渲染必需件，不算其他图表）
- 密钥纪律：.env 不进 git；验收产物（reports/*.md）不提交

## Task 1: 后端骨架与提示词层（history.py / output_schema.py / prompts/__init__.py）

目标：让 LLM 拿到可对比的历史数据，并定义对比输出字段。

1. `backend/stock_agent/history.py`
   - `extract_skeleton` 扩充，在现有字段基础上新增：
     - `financials`：取自 `module_3_财务健康.key_indicators`，精简为 `[{"name","value","trend"}]`（丢弃 verdict 控 token）
     - `price_trend`：取自 `module_4_股价走势.trend`（字符串）
     - `advice`：取自 `module_9_操作指南` 的 `{"buy_strategy","stop_loss","take_profit"}`
   - 移除 `signal_attribution` 的提取（现状提了但 `build_history_context` 从未使用，属死代码）；模块顶部 docstring 的字段列举同步更新
   - `build_history_context` 每份历史报告 section 增加三块渲染：财务指标每行 `- {name}：{value}（{trend}）`；股价走势一行；历史操作三要素三行
   - 头部标题 `## 历史报告回顾（该股票此前的分析结论，供对比参考）` 保持不变
   - 旧报告缺模块/字段为空时对应块不渲染、不报错
2. `backend/stock_agent/prompts/output_schema.py`
   - `module_9_操作指南` 内、`buy_strategy` 之前新增 4 字段：
     - `"history_anchor"`：对比基准的最近历史报告日期（YYYY-MM-DD）；无历史时整组 4 字段省略
     - `"history_compared"`：true（注入历史时必须为 true）
     - `"changed_aspects"`：变化方面数组，取值范围 财务面/股价面/操作建议；空数组 = 无变化
     - `"history_changes"`：条目化变化描述数组，每条 = 变化点 + 对比日期 + 对建议的影响；无变化时为空数组
3. `backend/stock_agent/prompts/__init__.py`
   - 删除旧指令句「若本次结论与历史结论存在差异，请在 module_1 核心逻辑中明确指出变化方向及原因。」
   - history_context 非空时追加的新指令：「你必须将该股历史报告与本次数据逐项对比（财务面、股价面、操作建议三块），并遵守：1. module_9 中 history_compared 必须为 true，history_anchor 填最近一份历史报告日期；2. 有变化 → changed_aspects 列出变化方面，history_changes 条目化描述（每条含对比日期与对建议的影响）；3. 无变化 → changed_aspects 与 history_changes 均置空数组；4. 建仓策略/止损参考/止盈参考必须基于与历史同三要素的对比分析后给出，若较历史有调整要说明原因。」
4. 测试：`backend/tests/test_history.py` 更新/新增——extract_skeleton 含新三块且不再含 signal_attribution；build_history_context 渲染含财务行/走势行/三要素行；旧报告缺模块不渲染不报错。`python -m pytest backend/tests/test_history.py -q` 通过
5. 回归：`sample_history_indices` 行为不变（doctest/既有用例通过）

## Task 2: 后端校验、渲染与 trend API（validator.py / analyze.py / render.py / stock_api.py）

1. `backend/stock_agent/validator.py`
   - `validate_report(report, has_history=False)` 加参（默认 False 保持旧调用兼容）
   - has_history=True 时新增规则（违规文案中文）：
     1. `module_9_操作指南.history_compared` 必须为 true，缺失或非 true → 违规
     2. `history_anchor` 非空且为 YYYY-MM-DD 形态 → 否则违规
     3. `changed_aspects` 必须为 list 且取值 ⊆ {财务面, 股价面, 操作建议} → 否则违规
     4. `changed_aspects` 非空 ⇔ `history_changes` 非空 → 不一致违规
   - has_history=False 时上述字段全部不检查
2. `backend/stock_agent/analyze.py`
   - `analyze_with_validation` 将 `has_history=bool(history_context)` 传入全部 `validate_report` 调用点（含修正后复查）
3. `backend/stock_agent/render.py`
   - 「## 九、散户实战操作指南」节顶部、建仓策略之前：
     - `history_changes` 非空 → 渲染 `**历史对比（基准：{history_anchor} 报告）：**` + 每条 `- {item}`
     - 否则 `history_compared` 为 true → 渲染 `- 与 {history_anchor} 报告对比无重大变化`
     - 字段均无 → 不渲染（存量报告兼容）
4. `backend/routers/stock_api.py`
   - 新增 `GET /api/stock/reports/trend/{stock_code}`：复用 `database.get_recent_reports`（倒序），反转为时间升序返回 `{"code":0,"data":[{"created_at": ..., "score": ...}]}`；score 为 None/非数的行跳过
5. 测试：validator 新规则单测——has_history=True 缺字段→违规；changed_aspects 非空但 history_changes 空→违规；取值越界→违规；has_history=False 无字段→不违规。render 三态各一断言。trend API 验证升序与跳过逻辑
6. 全量 `python -m pytest backend/tests -q` 通过

## Task 3: 后端单样本端到端验收

前置：直接在 master 工作目录执行；`backend/.env` 已存在（gitignore 覆盖，不提交）。

1. 查库选股（用 backend 的 DATABASE_URL）：`SELECT stock_code, COUNT(*) n FROM stock_reports GROUP BY stock_code HAVING n>=2 ORDER BY n DESC LIMIT 5`；选 n≥2 的股票；若无则退选 n=1；库空 → BLOCKED
2. 在 backend 目录跑 `python -m stock_agent.analyze <code>`（含 SKILL 采集 + LLM 分析 + 渲染），验收：
   1. stderr 出现「已注入 … 历史对比上下文」
   2. 报告 JSON 的 module_9 含 `history_compared=true` 与 `history_anchor`，且无 `_validation_issues` 涉及新规则
   3. 有变化时 `history_changes` 条目数字与注入骨架抽查一致；无变化时 `changed_aspects=[]` 且 MD 渲染「无重大变化」行
   4. MD 中 module_9 顶部对比块/轻提示位于建仓策略之前
3. trend API 验证：调用函数或起服务请求该 code，升序且含本次新报告点
4. N=0 抽查（若库中存在无历史的股票代码）：不注入、字段缺省、validator 不报违规
5. 验收记录（关键输出片段）写入 report 文件；`.env`、`reports/*.md` 产物不提交（先 `git status` 确认未跟踪）
6. 若 SKILL 采集因环境不可用失败 → BLOCKED 并附 stderr，不伪造结果

## Task 4: 前端趋势图与对比块

1. `frontend` 目录：node_modules 缺失先 `npm install`，再 `npm install echarts`
2. 新组件 `frontend/src/components/report/ScoreTrendChart.vue`
   - props：`points`（升序 `[{created_at, score}]`）
   - 按需引入：`echarts/core` + `LineChart`（echarts/charts）+ `GridComponent, TooltipComponent`（echarts/components）+ `CanvasRenderer`（echarts/renderers），`echarts.use([...])`
   - 样式浅色简约：线色取页面现有 accent/CSS 变量；Y 轴 0-100；X 轴时间（MM-DD HH:mm）；tooltip 显示分数
   - `points.length < 2` → 不初始化图表，浅色文案「首次报告，无历史趋势」
   - 尺寸适配 score-card 右侧空白（宽约 320~420px、高约 140~160px）；onUnmounted dispose
3. `frontend/src/stores/stock.js`：新增 `fetchTrend(code)` 调 trend API，存 `trendPoints`
4. `frontend/src/views/agent/StockReport.vue`：score-card 右侧嵌入 ScoreTrendChart；报告加载后以 `stock_code` 调 fetchTrend；不破坏现有两列 layout
5. `frontend/src/components/report/HoldingAdviceCard.vue`：module_9 顶部——`history_changes` 非空 → 标题「历史对比（基准：{history_anchor} 报告）」+ 条目列表，其下才建仓/止损/止盈；否则 `history_compared` 为 true → 浅色小字「与 {history_anchor} 报告对比无重大变化」；均无 → 不渲染
6. 验证：`npm run build` 通过；`npm test` 既有测试通过；风格与现有浅色简约一致
