# 技术跟踪台账（Tech Tracker）

> **长期维护文档**：统一记录代码优化、安全加固、已知问题与技术债务。
> **维护约定**（见 §5）：每完成一项相关工作，在对应条目更新状态与日期；新发现的问题随手登记进 §3。

---

## 一、已完成的优化与加固

### 1. Prompt 抽离重构 ｜ 2026-08-01 ｜ commit 3800bb8
- **内容**：analyze.py 内 177 行三层 prompt 抽为独立 `stock_agent/prompts/` 包（role_definition / core_rules / output_schema + `__init__.py` 组装函数）
- **改动**：4 新文件 + analyze.py（+190/-174）；模块级 import 天然 re-export，调用方与测试零改动
- **验证**：22 个测试全绿；AST 提取 git HEAD 版常量逐字对比，system/user prompt 零差异（纯搬移）
- **关联**：为 E0 验证器提供了规则锚点（三层 prompt 即校验规则来源）

### 2. E0 报告语义验证器 ｜ 2026-08-02 ｜ 已上线
- **内容**：analyze 产出 JSON 后跑 9 维硬规则校验（字段齐全/类型/score 范围/decision 枚举/模块子字段/财务指标≥4/利好利空≥1/风险≥2/权重和=1.0±0.05/score-decision 一致性）；违规则回传 LLM 定点修正 1 轮，仍违规附 `_validation_issues` 不阻塞
- **新增**：`stock_agent/validator.py`；`analyze.py` 新增 `analyze_with_validation()`（旧 `analyze()` 保持不变）
- **接入点 ×4**：stock_api 单股后台任务 / 自选股批量 / SSE 实时 / CLI main
- **验证**：单测 20 项 + 端到端 mock 3 项；DB 55 份真实报告回放 → 21 份全绿、33 份旧 schema 遗留（2026-07-16 升级前资产）、新格式仅 1 份真缺陷（decision 越枚举），零误报零漏报

### 3. E1 历史对比记忆 ｜ 2026-08-02 ｜ 已上线
- **内容**：生成报告时从 DB 取该股历史报告骨架注入 prompt，LLM 自发产出"与 X 月 X 日历史结论对比……变化方向……"
- **采样规则**（用户确认）：N≤2 全取；N≥3 取奇数位 [1,3,5,…]，封顶 5 份；只注入骨架（score/decision/rating_sentence/core_logic/signal_attribution），非全文
- **新增**：`stock_agent/history.py`、`database.get_recent_reports()`；`build_user_prompt(markdown, history_context="")` 向后兼容；4 调用点传入 stock_code
- **验证**：单测 9 项（采样边界全覆盖）+ 透传链路专测；原型 3 股 × 双版本：prompt 增量 +0.9%~3.2%（门槛 30%，A5 通过），有历史版全部写出显式历史对比、无历史版全无；A4 由用户直接确认价值引入

### 4. _parse_json 容错加固 ｜ 2026-08-02 ｜ 已上线
DeepSeek 输出故障的生产级容错，策略按序：默认宽松模式（strict=False）→ 未闭合字符串闭合 → 尾随逗号移除 → 裸引号启发式转义 → 栈逆序括号补全 → 最外层提取。max_retries 2→3。
- **第一轮**：字符串裸控制字符（E2 实验 000938 撞出）→ stdlib `strict=False`
- **第二轮**：未闭合字符串闭合 + 尾随逗号死条款修复（原匹配条件三条从未命中 CPython 真实报错 `Expecting property name`）
- **第三轮**：括号补全改栈逆序（突变回归暴露：旧计数补全无视嵌套顺序，signal_attribution 类"数组内嵌对象"深层截断救回率 0/21）+ 悬空转义符处理
- **第四轮**：裸引号启发式（错误位置前的可疑引号转义重试）+ 策略抢跑修复（错误位置在文中=裸引号、在文末=截断，防止括号补全抢占裸引号的重试次数）
- **验证**：容错单测 8 项；突变回归（21 份真实报告 × 4 类破坏）——截断加权救回率 ~22% → **~58%**，裸换行/尾随逗号/裸引号均 **21/21**

### 5. 测试资产增量 ｜ 2026-08-02
- 单测 30 → **61** 项全绿（validator 20 / history 9 / analyze 21 / render 11）
- 新增突变回归工具 `tests/parse_resilience_mutation.py`（零 LLM 成本量化救回率）

---

## 二、已评估-不引入（避坑记录）

| 方向 | 结论日期 | 依据 |
|---|---|---|
| E2 Reflection 质量自检 | 2026-08-02 **砍** | 10 股实验：评审员 100% 早停、发现问题 0 个、重写 0 次（橡皮图章化，A2 证伪）；附加 token +31%~+107%（均值 +63.5%，门槛 40%）——零收益高成本 |
| ReAct 数据自愈 | 2026-08-01 弃 | 东财 fallback 已存在、SKILL 工具集固定，无施展空间 |
| LangGraph 重构采集层 | 2026-08-01 弃 | SSE 双轨稳定，asyncio.gather 并行可解八成痛点，重构成本与收益不成比例 |
| HITL 推送确认 | 2026-08-01 弃 | 前端已有手动推送入口 |
| transformer 代码迁移 | 2026-08-01 弃 | 纯原理教学，价值是心智模型（长上下文稀释）与内训材料 |

完整论证见 `docs/discovery-framework-paradigm.md`。

---

## 三、已知问题与技术债务

> 严重度：🔴 高 / 🟡 中 / 🟢 低。状态：待修 / 观察 / 挂起 / 已修。

| # | 问题 | 类别 | 严重度 | 发现 | 状态 | 处理建议 |
|---|---|---|---|---|---|---|
| 1 | LLM 输出解析失败率偏高（E2 实验 10 股中 4 只触发解析故障） | 健壮性 | 🟡 | 2026-08-02 | 部分已修（容错加固后突变救回率 ~58%） | 观察线上实际失败率；必要时补"失败语料 dump"机制持续回放 |
| 2 | 失败语料 dump 机制 | 测试基建 | 🟢 | 2026-08-02 | **已建（2026-08-02）** | `_dump_parse_failure` 解析失败前落盘原文到 `reports/failures/`（已 gitignore）；回放工具 `tests/replay_failures.py`，语料积累后定期跑 |
| 3 | test_stock_api 系 1 failed + 23 errors（存量环境问题，非代码缺陷） | 测试基建 | 🟡 | 2026-07 | 待专修 | 单独排查环境依赖，恢复 API 层测试覆盖 |
| 4 | 港股代码双格式入库：HK2513 与 2513.HK 并存于 stock_reports | 数据一致性 | 🟡 | 2026-08-01 | 待修 | 历史数据迁移统一为归一化格式（generate_report_sync 已归一化，仅存量脏数据） |
| 5 | `stock_agent/models.py` 6 个 to_prompt_context() 死方法（旧管线遗留，2026-08-02 核实仅 test/probe 引用，生产链路零消费） | 死代码 | 🟢 | 2026-07 | 待清理 | 连同 test_models.py 对应用例一并移除 |
| 6 | 前端 `healthCheck` API 导出无消费者（2026-08-02 核实 frontend/src/api/index.js:27 仅定义） | 死代码 | 🟢 | 2026-07 | 待清理 | 接入健康检查界面或移除导出 |
| 7 | E3 模块化生成 / E4 多智能体辩论 | 挂起特性 | — | 2026-08-01 | 挂起观察 | E3 可治本解决长输出截断（#1 的根因之一），待容错加固的线上数据再决策；E4 带 kill gate |
| 8 | git 凭据助手残留警告 `credential-manager-core is not a git command` | 环境噪音 | 🟢 | 2026-07 | 无害 | 更新 git config credential.helper 可消除 |
| 9 | code-review-graph 钩子报 build_* "Untested" 假阳性（跨模块 re-export 识别不到） | 工具噪音 | 🟢 | 2026-08-01 | 无害 | 忽略，测试实际经 analyze re-export 覆盖 |
| 10 | **analyze.py 硬编码 OpenAI 端点，未接 .env 的 LLM_BASE_URL（anthropic）**：生产链路 DeepSeek 走 OpenAI 端点，与 .env 配置意图（两模型统一 anthropic）不一致；E4 辩论链顾问A 因复用 analyze 亦走 OpenAI（实验暂不改，用户指示生产环境修改时统一） | 配置一致性 | 🟡 | 2026-08-03 | 待生产改造 | 生产环境改造时全链统一 anthropic 端点：注意 OpenAI↔Anthropic 思考参数协议差异（extra_body thinking vs thinking 参数），改完全链路回归 |

---

## 四、测试资产清单

| 文件 | 性质 | 覆盖 |
|---|---|---|
| tests/test_validator.py | 单测（pytest） | 9 维校验规则逐条 + 合规基线防误报，20 项 |
| tests/test_history.py | 单测（pytest） | 采样规则边界全覆盖 + 骨架提取 + 坏行容错，9 项 |
| tests/test_analyze.py | 单测（pytest） | prompt 构建 / LLM mock / 数据守卫 / 容错解析 8 专项，21 项 |
| tests/test_render.py | 单测（pytest） | Markdown 渲染，11 项 |
| tests/parse_resilience_mutation.py | 突变回归（手动） | 21 份真实报告 × 4 类破坏，量化救回率；**不纳入 pytest，改动 _parse_json 后必跑** |
| tests/e1_history_ab.py | 实验脚本 | E1 历史对比 A/B 材料生成（单变量控制） |
| tests/e2_reflection_ab.py | 实验脚本 | E2 评审闭环 A/B（已砍，脚本留档可复现） |
| tests/e1_field_completeness.py | 实验脚本 | 字段完整度抽样（E0 验证器前身） |

---

## 五、维护约定

1. **条目化**：每项工作/问题一行或一节，必带日期与状态，不写长篇论证（论证放专题文档如 discovery-framework-paradigm.md，此处只留结论与指针）
2. **状态流转**：`待修/观察/挂起` → 完成后移入 §1 并标注 commit 或日期；砍掉的方向进 §2 留数据依据，避免日后重复论证
3. **核实优先**：登记代码事实前先 grep 核实（本台账 §3 各条均标注核实日期），代码变了条目随之更新
4. **回归纪律**：改动 `_parse_json` 必须跑 `parse_resilience_mutation.py`；改动 prompts 三层常量必须跑 test_analyze + test_validator
