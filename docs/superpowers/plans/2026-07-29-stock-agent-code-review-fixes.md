# Stock Agent 代码审查修复 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按分级修复阿里巴巴代码审查工具在 `backend/stock_agent` 中发现的 20 项问题（安全问题 2 项、功能缺陷 8 项、健壮性 6 项、死代码/文档 4 项），其中 1 项需先实证验证再定方案、1 项需用户批准（全局文件）。

**Architecture:** stock_agent 是股票分析功能的数据采集 + LLM 分析管线：前端 Vue（`frontend/src/api/index.js`）→ FastAPI 路由（`backend/routers/stock_api.py`）→ `skill/report.py` 编排 10 维度 iFinD SKILL 采集（`skill/__init__.py` → `~/.claude/skills/ifind-finance-data/call.py`）→ 生成 Markdown 数据报告 → `analyze.py` 调 DeepSeek Reasoner 分析 → `render.py` 渲染 9 模块报告 → SSE 流 / 数据库 / 飞书推送。本次修复只动 `backend/stock_agent/` 与全局 skill 的 `call.py`（SSL 项），不动前端。

**Tech Stack:** Python 3.x、pytest + unittest.mock（项目既有测试风格）、FastAPI、requests、OpenAI SDK（DeepSeek Reasoner）、iFinD MCP SKILL。

## Global Constraints

- **禁止新增依赖**：审查工具建议的 `httpx` 方案不采用（理由见"不修清单"第 1 条）；只用标准库与现有依赖。
- **命名与注释**：遵循项目既有 Python snake_case 风格；新增/修改处写中文注释。
- **Git 规范**：commit message 用 conventional commit 中文格式，禁止暴露 AI 写作痕迹。
- **测试命令**：`cd D:/karensAgent/backend && python -m pytest tests/<文件> -v`（基线：test_render + test_models 共 17 passed）。
- **局部修改原则**：每个任务只改 Files 区块列出的文件与行，不顺带重构无关代码。
- **iFinD 调用消耗配额**（免费版 2 QPS），实证验证任务（Task 2）最多 3 次调用。

---

## 背景：数据流向（工程师必读）

```
前端 Vue (api/index.js: triggerStockAnalyze / skill_report SSE)
  │
  ▼
backend/routers/stock_api.py
  ├─ _run_analysis()（后台线程）/ _run_watchlist_analyze()
  │    ① generate_report_sync(code)            ← skill/report.py
  │         └─ 10 维度 × call_skill()          ← skill/__init__.py
  │              └─ call.py → iFinD MCP (api-mcp.51ifind.com:8643, verify=False)
  │         └─ extract_text / extract_raw → _raw_to_prose → markdown + sections
  │         └─ performance 维度: _enrich_performance()
  │              └─ _fetch_ohlcv_eastmoney()   ← datasources/eastmoney.py (HTTP)
  │              └─ _calc_ma/macd/boll/rsi/kdj ← skill/indicators.py (纯数学)
  │         └─ _extract_stock_name() → 兜底 _get_name_eastmoney()
  │    ② analyze(markdown)                     ← analyze.py → DeepSeek Reasoner
  │    ③ render_markdown(code, report, usage, stock_name)  ← render.py
  │    ④ 存 reports/ 目录 + SQLite，前端轮询取结果
  └─ skill_report()（SSE 流式）: generate_report_stream() → 前端实时进度
```

**两个关键事实（影响修复优先级）：**

1. **`models.py` 的领域类（`MarketData`/`FinancialsData`/`ShareholderData` 等的 `to_frontend()`）在生产代码中零调用** —— 实际管线走 `skill/report.py` 的 prose 文本。生产只用到 `models.py` 的 `DataIncompleteError`。但 `tests/test_models.py` 对这些类有完整测试，故仍修复（零风险 + 防止未来复用时踩坑），优先级调低。
2. **`stock_api.py:323` 的飞书调用参数顺序是对的**（`push_to_feishu(row["markdown"], row["stock_name"], row["stock_code"])`），只有 `analyze.py:471` 的 CLI 入口传错了。

---

## 问题甄别结果（Triage）

对照 `D:\Desktop\1.txt` 的 20 条问题，逐条核实后的处置：

### A. 确认修复（9 项）

| # | 位置 | 问题 | 任务 |
|---|------|------|------|
| 1 | analyze.py:266 | API key 前缀泄漏到 stderr（security critical） | Task 1 |
| 2 | skill/__init__.py:11-12 | SSL 校验禁用（security high）—— 探针已验证 verify=True 可行 | Task 11（需批准） |
| 3 | analyze.py:471 | 飞书推送把 code 当 stock_name 传 | Task 5 |
| 4 | datasources/eastmoney.py:26,63 | 纯后缀代码 → `pure[0]` IndexError | Task 6 |
| 5 | render.py:26 | float 评分渲染空进度条 | Task 4 |
| 6 | render.py:107 | 表格单元格未转义 `\|` | Task 4 |
| 7 | skill/report.py:716,753 | async 生成器内同步 HTTP 阻塞事件循环 | Task 7 |
| 8 | skill/__init__.py:60,151 | `content[0]` 非 dict 时 AttributeError | Task 3 |
| 9 | analyze.py:341 | 贪婪正则 `\{.*\}` 提取 JSON 会越界匹配 | Task 10 |

### B. 先验证再定方案（1 项）

| # | 位置 | 问题 | 处置 |
|---|------|------|------|
| 10 | skill/__init__.py:73,164 | 审查工具称 `code == 0` 把成功判为失败 | **Task 2 实证验证**。反证：系统当前能正常采集数据出报告（三个实验全部通过），若 0=成功，所有数据早被丢弃、系统不可能工作。审查工具是按"0=成功"的通用惯例猜的，无证据。**禁止盲改方向**，先抓真实响应再定。 |

### C. 防御性/低优先修复（5 项）

| # | 位置 | 问题 | 任务 |
|---|------|------|------|
| 11 | analyze.py:30-32 | `.env` 缺失直接 FileNotFoundError 崩溃 | Task 5 |
| 12 | datasources/eastmoney.py:40,111 | 裸 `except Exception` 吞一切异常 | Task 6 |
| 13 | skill/indicators.py:136-137 | `hi`/`lo` 死代码；部分指标函数无 None 防御 | Task 8 |
| 14 | models.py:39,289,437,455 | `.strip()` 对非 str 崩溃、0 值被 falsy 丢弃（死代码但有测试） | Task 9 |
| 15 | skill/report.py:156-164 | HK 代码兜底返回 `.SH`（潜在，当前无触发路径） | Task 7 |

### D. 文档/清理（3 项）

| # | 位置 | 问题 | 任务 |
|---|------|------|------|
| 16 | skill/report.py:179 | 函数内重复 `import re as _re` | Task 7 |
| 17 | skill/__init__.py:136-141 | docstring 漏了 `json` 返回类型 | Task 3 |
| 18 | models.py:10 | `Any` 未使用导入 | Task 9 |

### E. 不修清单（3 项，附理由，需王磊哥哥确认）

1. **analyze.py:361 `push_to_feishu` 改 httpx 异步** — 不修（YAGNI）。当前无任何异步调用方：`main()` 顺序执行、`stock_api.py` 在后台线程调用，阻塞无影响；`httpx` 是新依赖（违反 Global Constraints）。若未来引入并发分析，用 `loop.run_in_executor` 包一层即可，无需改签名。
2. **models.py:235 `ShareholderData` 硬编码 iFind 字段名** — 不修。十大股东字段名是同花顺官方约定（含 `第{rank}名` 排名模板），非随意硬编码；且该类目前是死代码。仅加观察性注释（Task 9 附带）。
3. **skill/__init__.py:14-16 `sys.path` 副作用改 importlib** — 不大改。这是加载 `~/.claude/skills/` 下共享 skill 的既有机制，改 importlib 牵动全局、风险高收益低；仅加 NOTE 注释说明（Task 3 附带）。

### 待决策（1 项）

- **render.py:10 未使用的 `usage` 参数**：审查工具建议"要么用起来，要么删掉"。删除需改 3 个调用方（analyze.py:454、stock_api.py:99、stock_api.py:155）；用起来则可在报告页脚渲染 token 消耗（dogfooding 阶段有用）。**本计划默认采用"用起来：页脚加一行 token 消耗"**（见 Task 4），如王磊哥哥倾向删除，请告知。

---

## File Structure

| 文件 | 操作 | 职责变化 |
|------|------|----------|
| `backend/stock_agent/analyze.py` | Modify | 诊断日志脱敏；`.env` 缺失友好提示；JSON 提取改括号深度；飞书参数修正；usage 保留 |
| `backend/stock_agent/render.py` | Modify | 新增 `_escape_cell()` 辅助函数；评分条兼容 float；页脚渲染 usage |
| `backend/stock_agent/skill/__init__.py` | Modify | `content[0]` 类型守卫；docstring 补全；code 判断按 Task 2 结论处理 |
| `backend/stock_agent/skill/report.py` | Modify | 阻塞调用包 executor；`_market_suffix` HK 显式报错；删重复 import |
| `backend/stock_agent/skill/indicators.py` | Modify | 删死代码；窗口函数 None 防御；docstring 输入契约 |
| `backend/stock_agent/datasources/eastmoney.py` | Modify | 空代码守卫；异常类型收窄；`.get("data") or {}` |
| `backend/stock_agent/models.py` | Modify | `_iter_fields`/`_first_of` 类型安全；删无用导入 |
| `~/.claude/skills/ifind-finance-data/call.py` | Modify（需批准） | `verify=False` → `verify=True` |
| `backend/tests/test_analyze.py` | Modify | 新增 key 泄漏、JSON 提取测试 |
| `backend/tests/test_render.py` | Modify | 新增 float 评分、管道符转义测试 |
| `backend/tests/test_skill_extract.py` | Create | extract_text/extract_raw 守卫测试 |
| `backend/tests/test_eastmoney.py` | Create | 空代码守卫测试 |
| `backend/tests/test_report_unit.py` | Create | `_market_suffix` 测试 |
| `backend/tests/test_indicators.py` | Create | 指标 None 防御测试 |
| `backend/tests/test_models.py` | Modify | 新增数值/0 值测试 |
| `backend/tests/probe_code_convention.py` | Create→Delete | Task 2 临时探针，验证完删除 |

---

## Task 1: analyze.py — API key 泄漏修复（security critical）

**Files:**
- Modify: `backend/stock_agent/analyze.py:264-267`
- Test: `backend/tests/test_analyze.py`（追加）

**Interfaces:**
- Produces: `analyze()` 行为不变（返回 `(report, usage)`），仅 stderr 诊断日志内容变化。

- [ ] **Step 1: 写失败测试**

在 `backend/tests/test_analyze.py` 末尾 `if __name__` 块之前追加：

```python
def test_analyze_stderr_does_not_leak_api_key(monkeypatch, capsys):
    """诊断日志禁止包含 API key 的任何片段（只允许记录长度等元数据）"""
    fake_key = "sk-testkey-1234567890abcdef"
    monkeypatch.setenv("DEEPSEEK_API_KEY", fake_key)

    from stock_agent.analyze import analyze

    with patch('stock_agent.analyze.OpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_completion = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = '{"score":75,"decision":"看多"}'
        mock_choice.finish_reason = "stop"
        mock_completion.choices = [mock_choice]
        mock_completion.usage.prompt_tokens = 10
        mock_completion.usage.completion_tokens = 10
        mock_completion.usage.total_tokens = 20
        mock_client.chat.completions.create.return_value = mock_completion

        analyze("# 测试报告\n有内容")

    err = capsys.readouterr().err
    assert fake_key not in err, "API key 完整泄漏到 stderr"
    assert fake_key[:15] not in err, "API key 前缀泄漏到 stderr"
    assert "key_len=" in err, "应改为只记录 key 长度"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd D:/karensAgent/backend && python -m pytest tests/test_analyze.py::test_analyze_stderr_does_not_leak_api_key -v`
Expected: FAIL — `AssertionError: API key 前缀泄漏到 stderr`（当前日志打印 `key={api_key[:15]}...`）

- [ ] **Step 3: 最小实现**

修改 `backend/stock_agent/analyze.py:264-267`：

```python
    # 诊断日志（安全：只记录 key 长度，禁止输出 key 内容，防止日志系统泄密）
    import sys as _sys
    print(f"[analyze] key_len={len(api_key)} sys_prompt_len={len(build_system_prompt())} user_prompt_len={len(user_prompt)}", file=_sys.stderr)
    print(f"[analyze] content_len={len(content) if content else 0} reasoning_len={len(reasoning_content) if reasoning_content else 0} finish_reason={resp.choices[0].finish_reason}", file=_sys.stderr)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd D:/karensAgent/backend && python -m pytest tests/test_analyze.py -v`
Expected: 全部 PASS（含既有 6 个测试）

- [ ] **Step 5: 提交**

```bash
cd D:/karensAgent && git add backend/stock_agent/analyze.py backend/tests/test_analyze.py
git commit -m "fix(stock_agent): 诊断日志移除 API key 前缀，改为只记录长度"
```

---

## Task 2: 实证验证 iFinD 内层 code 字段约定（决定 Task 3 的改法）

**这不是代码修复任务，是验证任务。产出：验证结论 + 处置决策。**

背景：`skill/__init__.py:73` 和 `:164` 的 `if inner.get("code") == 0: return 失败` 被审查工具判定为"反转"，建议改成 `!= 0`。**但系统当前能正常采集全部 10 维度数据并出报告**——若成功响应的 code 真是 0，所有数据会被判为"[权限不足或无数据]"而丢弃，系统不可能正常工作。所以审查工具的猜测大概率是错的，必须用真实响应验证。

**Files:**
- Create（临时）: `backend/tests/probe_code_convention.py`（验证完删除）

- [ ] **Step 1: 编写探针脚本**

创建 `backend/tests/probe_code_convention.py`：

```python
"""临时探针：实证 iFinD MCP 响应内层 code 字段约定（成功/失败各是什么值）

运行: cd D:/karensAgent/backend && python tests/probe_code_convention.py
消耗 iFinD 配额约 3 次调用，验证后删除本文件。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from stock_agent.skill import call_skill


def probe(label: str, server: str, tool: str, params: dict):
    """调用一次 SKILL，打印内层原始结构（绕过 extract_text 的 code 判断）"""
    result = call_skill(server, tool, params)
    print(f"\n{'='*60}\n=== {label} ===")
    print(f"外层 ok={result.get('ok')} status_code={result.get('status_code')}")
    if not result.get("ok"):
        print(f"外层错误（call.py 已拦截，看不到内层）: {result.get('error')}")
        return
    content = result.get("data", {}).get("result", {}).get("content", [])
    if not content:
        print("content 为空")
        return
    first = content[0]
    print(f"content[0] 类型: {type(first).__name__}")
    if not isinstance(first, dict):
        print(f"content[0] 非 dict: {first!r}")
        return
    raw_text = first.get("text", "")
    try:
        inner = json.loads(raw_text)
    except (json.JSONDecodeError, TypeError):
        print(f"内层不是 JSON: {raw_text[:200]}")
        return
    if not isinstance(inner, dict):
        print(f"内层不是 dict: {type(inner).__name__}")
        return
    print(f"内层 keys: {list(inner.keys())}")
    print(f"内层 code = {inner.get('code')!r}  (类型: {type(inner.get('code')).__name__})")
    print(f"内层 msg  = {inner.get('msg', '')!r}")
    data = inner.get("data")
    print(f"内层 data 类型 = {type(data).__name__}, 非空 = {bool(data)}")


# 用例 1：正常成功（预期拿到数据）
probe("成功用例：茅台基本信息", "stock", "get_stock_summary",
      {"query": "股票代码600519的基本信息"})

# 用例 2：范围外应答（A股服务查港股，预期"不属于数据范围"）
probe("范围外用例：A股服务查港股", "stock", "get_stock_summary",
      {"query": "港股02513的基本信息"})

# 用例 3：无效代码（预期无数据或错误）
probe("无效用例：不存在的代码", "stock", "get_stock_summary",
      {"query": "股票代码999999的基本信息"})

print("\n" + "=" * 60)
print("验证完毕。请记录上面三个用例的 code 值，然后删除本脚本。")
```

- [ ] **Step 2: 运行探针并记录结果**

Run: `cd D:/karensAgent/backend && python tests/probe_code_convention.py`
Expected: 打印三个用例的内层 `code` 值。记录到本计划文档此处的"验证记录"表（执行时填写）：

| 用例 | 内层 code 值 | 内层 data | 结论 |
|------|-------------|-----------|------|
| 成功（茅台） | ____ | ____ | ____ |
| 范围外（港股） | ____ | ____ | ____ |
| 无效代码 | ____ | ____ | ____ |

- [ ] **Step 3: 按决策树定方案**

- **若成功响应 code 为 None 或非 0**（预期如此，与系统现状一致）：当前 `== 0` 逻辑**正确**，约定是"0=失败/权限不足"。Task 3 中**不改判断方向**，只把注释改明确 + 错误提示文案改准确。
- **若成功响应 code 恰为 0**（与系统现状矛盾，极不可能）：逻辑确实反转，Task 3 中把 `== 0` 改为 `!= 0`，并回归跑一遍完整采集确认。
- **无论哪种**：Task 3 都增加"data 为空兜底"——code 检查通过后若 `inner.get("data")` 为空（None/""/空 dict），按无数据处理，不再依赖单一 code 语义。

- [ ] **Step 4: 删除探针脚本**

```bash
rm D:/karensAgent/backend/tests/probe_code_convention.py
```

（本任务不提交代码；验证结论写入 Task 3 的实现注释中。）

---

## Task 3: skill/__init__.py — 类型守卫 + docstring + code 判断定性

**Files:**
- Modify: `backend/stock_agent/skill/__init__.py:11-16,60,136-141,151,72-78,163-169`
- Test: `backend/tests/test_skill_extract.py`（新建）

**Interfaces:**
- Consumes: Task 2 的验证结论（决定 code 判断是改方向还是只改注释）。
- Produces: `extract_text(result) -> str` 与 `extract_raw(result) -> dict | None` 签名不变，对畸形输入不再抛 AttributeError。

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_skill_extract.py`：

```python
"""skill/__init__.py 提取函数防御性测试

测试目标:
  1. content[0] 非 dict 时不抛 AttributeError
  2. 正常路径行为不变
"""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))


def test_extract_text_non_dict_content():
    """content[0] 是纯字符串时，应降级返回文本而非崩溃"""
    from stock_agent.skill import extract_text

    result = {"ok": True, "data": {"result": {"content": ["我就是纯文本"]}}}
    out = extract_text(result)  # 当前实现会抛 AttributeError
    assert isinstance(out, str)
    assert "纯文本" in out


def test_extract_text_non_dict_content_number():
    """content[0] 是数字时同样不能崩"""
    from stock_agent.skill import extract_text

    result = {"ok": True, "data": {"result": {"content": [12345]}}}
    out = extract_text(result)
    assert isinstance(out, str)


def test_extract_raw_non_dict_content():
    """extract_raw 同样需要守卫"""
    from stock_agent.skill import extract_raw

    result = {"ok": True, "data": {"result": {"content": [None]}}}
    out = extract_raw(result)  # 当前实现会抛 AttributeError
    assert out is None or isinstance(out, dict)


def test_extract_text_normal_path_unchanged():
    """正常 MCP 包装格式的提取行为不受守卫影响"""
    import json
    from stock_agent.skill import extract_text

    inner = {"data": {"answer": "公司全称：贵州茅台酒股份有限公司"}}
    result = {"ok": True, "data": {"result": {"content": [
        {"type": "text", "text": json.dumps(inner, ensure_ascii=False)}
    ]}}}
    out = extract_text(result)
    assert "贵州茅台" in out


def test_extract_text_empty_data_fallback():
    """code 检查通过但 data 为空时，按无数据处理（Task 2 决策树通用项）"""
    import json
    from stock_agent.skill import extract_text

    # 内层有 code（非失败值）但 data 为 None
    inner = {"code": 200, "msg": "", "data": None}
    result = {"ok": True, "data": {"result": {"content": [
        {"type": "text", "text": json.dumps(inner)}
    ]}}}
    out = extract_text(result)
    # 现状：data is None → return raw_text；保持该兜底不崩即可
    assert isinstance(out, str)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd D:/karensAgent/backend && python -m pytest tests/test_skill_extract.py -v`
Expected: 前 3 个 FAIL（`AttributeError: 'str' object has no attribute 'get'` 等），后 2 个 PASS。

- [ ] **Step 3: 最小实现**

修改 `backend/stock_agent/skill/__init__.py`：

**3a. 头部注释（11-16 行）**——按 Task 11 是否批准分两种，本任务先只加 NOTE，SSL 改动留给 Task 11：

```python
# 禁用 SSL 警告（call.py 使用 verify=False）
# TODO(security): call.py 的 verify=False 存在 MITM 风险，修复见 Task 11
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

SKILL_DIR = str(Path("~/.claude/skills/ifind-finance-data").expanduser())
if SKILL_DIR not in sys.path:
    # NOTE: 导入期修改全局 sys.path 是加载用户级共享 skill 的既有机制，
    # 改 importlib 作用域加载牵动面大，暂保留（见实施计划"不修清单"第 3 条）
    sys.path.insert(0, SKILL_DIR)
```

**3b. extract_text 守卫（55-74 行区域）**：

```python
    data = result.get("data", {})
    content = data.get("result", {}).get("content", [])
    if not content:
        return "[无数据]"

    # 守卫：MCP 异常响应下 content[0] 可能不是 dict
    first = content[0]
    if not isinstance(first, dict):
        return str(first)

    raw_text = first.get("text", "")
    if not raw_text:
        return "[空响应]"
```

以及 code 判断处（按 Task 2 结论二选一）：

```python
    # 检查内层 code 字段
    # 约定（Task 2 于 2026-07-XX 实证确认）：iFinD 内层 code=0 表示失败/权限不足，
    # 成功响应 code 为 <实测值>。系统正常运行即依赖此约定，勿按"0=成功"的通用惯例改。
    if inner.get("code") == 0:
        return f"[权限不足或无数据] {inner.get('msg', '')}"
```

（若 Task 2 意外证实成功 code=0，则上面条件改为 `!= 0`，注释同步反转。）

**3c. extract_raw 守卫（146-151 行区域）**：

```python
    data = result.get("data", {})
    content = data.get("result", {}).get("content", [])
    if not content:
        return None

    # 守卫：MCP 异常响应下 content[0] 可能不是 dict
    first = content[0]
    if not isinstance(first, dict):
        return {"type": "text", "text": str(first)}

    raw_text = first.get("text", "")
    if not raw_text:
        return None
```

（extract_raw 的 `code == 0` 处（约 163-165 行）按与 3b 相同的结论同步处理。）

**3d. docstring 补全（136-141 行区域）**：

```python
    """从 SKILL 返回结果中提取原始结构化数据（不做 Markdown 格式化）

    返回 typed dict，方便 prose formatter 按维度处理：
      {"type": "table",  "tables": [[...], ...]}     — 表格数据
      {"type": "news",   "articles": [{...}, ...]}    — 新闻/公告列表
      {"type": "answer", "text": "..."}               — 自然语言回答（可能内含表格）
      {"type": "json",   "data": {...}}               — 非表格的结构化 JSON
      {"type": "text",   "text": "..."}               — 纯文本/兜底
      None                                              — 错误或无数据
    """
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd D:/karensAgent/backend && python -m pytest tests/test_skill_extract.py -v`
Expected: 5 个全 PASS。

- [ ] **Step 5: 提交**

```bash
cd D:/karensAgent && git add backend/stock_agent/skill/__init__.py backend/tests/test_skill_extract.py
git commit -m "fix(stock_agent): extract_text/extract_raw 增加 content 类型守卫并补全 docstring"
```

---

## Task 4: render.py — float 评分进度条 + 管道符转义 + usage 页脚

**Files:**
- Modify: `backend/stock_agent/render.py:10,24-30,98-107,267-271`
- Test: `backend/tests/test_render.py`（追加）

**Interfaces:**
- Produces: `render_markdown(stock_code, report, usage, stock_name="") -> str` 签名不变；`usage["total"]` 渲染进页脚。

- [ ] **Step 1: 写失败测试**

在 `backend/tests/test_render.py` 的 `if __name__` 块之前追加：

```python
def test_render_markdown_float_score():
    """浮点评分（如 85.5）应按比例渲染进度条，而不是空条"""
    from stock_agent.render import render_markdown

    report = {"score": 85.5, "decision": "看多"}
    md = render_markdown("600519", report, {"total": 100})
    # int(85.5 / 100 * 20) = 17 格
    assert "█" * 17 + "░" * 3 in md, "浮点评分应渲染 17 格进度条"


def test_render_markdown_numeric_string_score():
    """字符串数字评分（如 LLM 偶发返回 "85"）也应正常渲染"""
    from stock_agent.render import render_markdown

    report = {"score": "85", "decision": "看多"}
    md = render_markdown("600519", report, {"total": 100})
    assert "█" * 17 + "░" * 3 in md


def test_render_markdown_invalid_score_empty_bar():
    """非数字评分（N/A）渲染空条且不崩溃"""
    from stock_agent.render import render_markdown

    report = {"score": "N/A", "decision": "震荡"}
    md = render_markdown("600519", report, {"total": 100})
    assert "░" * 20 in md


def test_render_markdown_pipe_escaped():
    """模块3 表格字段含管道符时应转义，避免破坏 Markdown 表格布局"""
    from stock_agent.render import render_markdown

    report = {
        "score": 60,
        "decision": "震荡",
        "module_3_财务健康": {
            "key_indicators": [
                {"name": "毛利率|扣非口径", "value": "89%|同比", "trend": "稳定", "verdict": "良好"},
            ],
        },
    }
    md = render_markdown("600519", report, {"total": 100})
    assert "毛利率\\|扣非口径" in md
    assert "89%\\|同比" in md


def test_render_markdown_usage_footer():
    """页脚应渲染 token 消耗（usage 参数不再是死参数）"""
    from stock_agent.render import render_markdown

    report = {"score": 75, "decision": "看多"}
    md = render_markdown("600519", report, {"prompt": 5000, "completion": 2000, "total": 7000})
    assert "7000" in md
    assert "Token" in md
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd D:/karensAgent/backend && python -m pytest tests/test_render.py -v`
Expected: 新增 5 个 FAIL（float 评分空条、管道符未转义、无 usage 页脚），既有测试 PASS。

- [ ] **Step 3: 最小实现**

修改 `backend/stock_agent/render.py`：

**3a. 文件头部加辅助函数（`from datetime import datetime` 之后）**：

```python
def _escape_cell(value) -> str:
    """转义 Markdown 表格单元格中的管道符，防止破坏表格布局"""
    return str(value).replace("|", "\\|")
```

**3b. 评分条（24-30 行）**：

```python
    # 评分条（兼容 int / float / 数字字符串；非法值渲染空条）
    bar_len = 20
    try:
        filled = int(float(score) / 100 * bar_len)
        filled = max(0, min(bar_len, filled))  # 越界评分钳制到 [0, bar_len]
    except (ValueError, TypeError):
        filled = 0
    bar = "█" * filled + "░" * (bar_len - filled)
```

**3c. 模块3 表格行（107 行）**：

```python
                out.append(f"| {_escape_cell(name)} | {_escape_cell(val)} | {_escape_cell(trend)} | {_escape_cell(verdict)} |")
```

**3d. 页脚（267-271 行）**——`usage` 参数用起来：

```python
    out.append("")
    out.append("---")
    out.append(f"*生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    # token 消耗（dogfooding 阶段跟踪成本用）
    total_tokens = usage.get("total") if isinstance(usage, dict) else None
    if total_tokens is not None:
        out.append(f"*Token 消耗：{total_tokens}*")
    out.append("*以上分析仅供参考，不构成投资建议。股市有风险，投资需谨慎。*")
```

**3e. docstring（11-18 行）** 中 `usage` 的说明改为：

```python
        usage: token 用量信息（渲染到报告页脚）
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd D:/karensAgent/backend && python -m pytest tests/test_render.py -v`
Expected: 全部 PASS（既有 + 新增）。

- [ ] **Step 5: 提交**

```bash
cd D:/karensAgent && git add backend/stock_agent/render.py backend/tests/test_render.py
git commit -m "fix(stock_agent): 评分条兼容浮点分、表格转义管道符、页脚渲染 token 消耗"
```

---

## Task 5: analyze.py — 飞书参数顺序 + .env 缺失友好提示

**Files:**
- Modify: `backend/stock_agent/analyze.py:29-38,471`

**Interfaces:**
- Produces: `main()` 行为修正；模块导入在无 `.env` 时不再崩溃。
- 注意：`analyze.py` 会被 `stock_api.py:317` 导入（`from stock_agent.analyze import push_to_feishu`），所以 **`.env` 缺失时绝不能 `sys.exit(1)`**（审查工具的建议会拖垮整个后端），只能警告后继续。

- [ ] **Step 1: 修复 .env 缺失处理（29-38 行）**

```python
# 读取 .env（缺失时警告并继续，不能 exit —— 本模块会被 stock_api 导入复用 push_to_feishu）
env_path = Path(__file__).resolve().parent.parent / ".env"
env_vars = {}
if not env_path.exists():
    print(f"⚠️ 未找到 .env 文件: {env_path}，LLM 分析与飞书推送将不可用", file=sys.stderr)
else:
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            env_vars[key.strip()] = value.strip()
```

- [ ] **Step 2: 修复飞书参数顺序（471 行）**

```python
        # 飞书推送（第 2 参是 stock_name，453 行已从采集结果提取，勿再传 code）
        if args.push:
            push_to_feishu(md, stock_name, code)
```

- [ ] **Step 3: 手动验证 .env 缺失路径**

```bash
cd D:/karensAgent/backend
mv .env .env.bak
python -c "import stock_agent.analyze" ; echo "exit=$?"
mv .env.bak .env
```

Expected: 打印 `⚠️ 未找到 .env 文件: ...`，`exit=0`（导入成功，不崩溃）。恢复 `.env` 后再跑 `python -c "import stock_agent.analyze"` 无警告。

- [ ] **Step 4: 手动验证飞书标题**

（可选，需配置 FEISHU_STOCK_WEBHOOK_URL 且消耗一次 LLM 配额）

Run: `cd D:/karensAgent/backend && python -m stock_agent.analyze 600398 --push`
Expected: 飞书卡片标题为"海澜之家（600398）分析报告"而不是"600398（600398）..."。若不便实测，以 code review 为准（`stock_api.py:323` 的同名调用已验证过该签名约定）。

- [ ] **Step 5: 回归既有测试 + 提交**

Run: `cd D:/karensAgent/backend && python -m pytest tests/test_analyze.py -v`
Expected: PASS。

```bash
cd D:/karensAgent && git add backend/stock_agent/analyze.py
git commit -m "fix(stock_agent): 飞书推送传股票名称而非代码；.env 缺失时警告而非崩溃"
```

---

## Task 6: datasources/eastmoney.py — 空代码守卫 + 异常收窄

**Files:**
- Modify: `backend/stock_agent/datasources/eastmoney.py:19-28,30-42,56-65,67-112`
- Test: `backend/tests/test_eastmoney.py`（新建）

**Interfaces:**
- Produces: `_get_name_eastmoney(stock_code) -> str | None`、`_fetch_ohlcv_eastmoney(stock_code) -> dict | None` 签名与 None 兜底语义不变。

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_eastmoney.py`：

```python
"""东方财富数据源防御性测试

测试目标:
  1. 纯后缀/空代码不抛 IndexError（守卫在 HTTP 之前，测试不走网络）
  2. secid 构造逻辑正确
"""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))


def test_get_name_empty_code_guard():
    """'.SH' 剥后缀为空，应返回 None 而不是 IndexError"""
    from stock_agent.datasources.eastmoney import _get_name_eastmoney

    assert _get_name_eastmoney(".SH") is None
    assert _get_name_eastmoney(".SZ") is None
    assert _get_name_eastmoney("   ") is None


def test_fetch_ohlcv_empty_code_guard():
    from stock_agent.datasources.eastmoney import _fetch_ohlcv_eastmoney

    assert _fetch_ohlcv_eastmoney(".SH") is None
    assert _fetch_ohlcv_eastmoney("") is None


def test_hk_code_zfill(monkeypatch):
    """港股 secid 应为 116.{5位补零}，且走港股分支不受 A 股守卫影响"""
    import stock_agent.datasources.eastmoney as em

    captured = {}

    class FakeResp:
        def json(self):
            return {"data": {"f58": "美图公司"}}

    def fake_get(url, params=None, timeout=None):
        captured["params"] = params
        return FakeResp()

    monkeypatch.setattr(em.requests, "get", fake_get)
    name = em._get_name_eastmoney("2513.HK")
    assert name == "美图公司"
    assert captured["params"]["secid"] == "116.02513"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd D:/karensAgent/backend && python -m pytest tests/test_eastmoney.py -v`
Expected: 前 2 个 FAIL（`IndexError: string index out of range`），第 3 个 PASS。

- [ ] **Step 3: 最小实现**

修改 `backend/stock_agent/datasources/eastmoney.py`：

**3a. `_get_name_eastmoney`（19-42 行）**：

```python
def _get_name_eastmoney(stock_code: str) -> str | None:
    """东方财富 HTTP 直调查询公司名称，A股+港股通用

    作为 iFinD 正则提取失败时的兜底方案。
    secid 规则：沪市 1.{code}，深市 0.{code}，港股 116.{zfill(5)}
    """
    code = stock_code.strip()
    # 港股 secid：116. + 零填充到5位
    if code.endswith(".HK"):
        pure = code.replace(".HK", "")
        if not pure:  # 守卫：纯后缀输入（如 ".HK"）
            return None
        secid = f"116.{pure.zfill(5)}"
    else:
        # A股：清掉 .SH/.SZ 后缀，按首字判断市场
        pure = code.replace(".SH", "").replace(".SZ", "")
        if not pure:  # 守卫：空代码或纯后缀（如 ".SH"），避免 pure[0] IndexError
            return None
        market = "1" if pure[0] in ("6", "5") else "0"
        secid = f"{market}.{pure}"

    # 收窄异常：网络错误 / JSON 解析 / 字段缺失分别对应明确类型，不再裸吞 Exception
    try:
        r = requests.get(
            "https://push2.eastmoney.com/api/qt/stock/get",
            params={"fltt": "2", "invt": "2", "fields": "f57,f58", "secid": secid},
            timeout=5,
        )
        data = r.json()
        name = (data.get("data") or {}).get("f58", "")  # data 字段可能为 None
        if name and len(name) >= 2:
            return name
    except (requests.RequestException, ValueError, KeyError, TypeError):
        # ValueError 覆盖 JSONDecodeError；TypeError/KeyError 覆盖响应结构异常
        pass
    return None
```

**3b. `_fetch_ohlcv_eastmoney`（56-112 行）**——同样两处守卫 + 异常收窄：

```python
    code = stock_code.strip()

    # 构造东财 secid：港股 116.{zfill(5)}，沪市 1.{code}，深市 0.{code}
    if code.endswith(".HK"):
        pure = code.replace(".HK", "")
        if not pure:
            return None
        secid = f"116.{pure.zfill(5)}"
    else:
        pure = code.replace(".SH", "").replace(".SZ", "")
        if not pure:  # 守卫：空代码或纯后缀，避免 pure[0] IndexError
            return None
        market = "1" if pure[0] in ("6", "5") else "0"
        secid = f"{market}.{pure}"

    try:
        r = requests.get(
            "https://push2his.eastmoney.com/api/qt/stock/kline/get",
            params={
                "secid": secid,
                "fields1": "f1,f2,f3,f4,f5,f6",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                "klt": "101",       # 日K
                "fqt": "1",         # 前复权
                "end": "20500101",
                "lmt": "70",        # 取70条保证覆盖60个交易日
            },
            timeout=10,
        )
        data = r.json()
        klines = (data.get("data") or {}).get("klines")  # data 字段可能为 None
        if not klines:
            return None
```

（函数体余下解析逻辑不动，仅把末尾 `except Exception:` 改为：）

```python
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return None
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd D:/karensAgent/backend && python -m pytest tests/test_eastmoney.py -v`
Expected: 3 个全 PASS。

- [ ] **Step 5: 提交**

```bash
cd D:/karensAgent && git add backend/stock_agent/datasources/eastmoney.py backend/tests/test_eastmoney.py
git commit -m "fix(stock_agent): 东财数据源空代码守卫防 IndexError，收窄裸异常"
```

---

## Task 7: skill/report.py — 阻塞 I/O 包 executor + HK 后缀 + 重复 import

**Files:**
- Modify: `backend/stock_agent/skill/report.py:156-164,177-182,714-716,753`
- Test: `backend/tests/test_report_unit.py`（新建）

**Interfaces:**
- Produces: `generate_report_stream()` 对外 SSE 协议不变；`_market_suffix(".HK")` 行为由"静默返回 .SH"改为抛 `ValueError`（快速失败，当前生产路径不会触发）。

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_report_unit.py`：

```python
"""skill/report.py 纯函数单元测试

测试目标:
  1. _market_suffix 各市场后缀正确
  2. 港股代码误调用后缀函数时快速失败（而非静默拼出错误后缀）
"""
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))


def test_market_suffix_sh():
    from stock_agent.skill.report import _market_suffix
    assert _market_suffix("600519") == ".SH"
    assert _market_suffix("688981") == ".SH"


def test_market_suffix_sz():
    from stock_agent.skill.report import _market_suffix
    assert _market_suffix("000858") == ".SZ"
    assert _market_suffix("002415") == ".SZ"  # 002 前缀由 00 覆盖
    assert _market_suffix("003032") == ".SZ"  # 003 前缀由 00 覆盖
    assert _market_suffix("300750") == ".SZ"


def test_market_suffix_bj():
    from stock_agent.skill.report import _market_suffix
    assert _market_suffix("830799") == ".BJ"
    assert _market_suffix("430047") == ".BJ"


def test_market_suffix_hk_raises():
    """港股应走 global_stock 服务（query_tpl 分支），后缀函数被误调用时必须大声报错"""
    from stock_agent.skill.report import _market_suffix
    with pytest.raises(ValueError):
        _market_suffix("2513.HK")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd D:/karensAgent/backend && python -m pytest tests/test_report_unit.py -v`
Expected: `test_market_suffix_hk_raises` FAIL（当前返回 ".SH" 不抛异常），其余 PASS。

- [ ] **Step 3: 最小实现**

修改 `backend/stock_agent/skill/report.py`：

**3a. `_market_suffix`（156-164 行）**：

```python
def _market_suffix(stock_code: str) -> str:
    """根据股票代码判断交易所后缀（仅 A 股；港股走 global_stock 服务不拼后缀）"""
    if stock_code.endswith(".HK"):
        # 港股维度用 query_tpl 分支，从不需要后缀；误调用时快速失败，
        # 防止静默拼出 "2513.HK.SH" 这类错误代码
        raise ValueError(f"港股代码 {stock_code} 不应走 A 股后缀逻辑（应用 global_stock 服务）")
    if stock_code.startswith(("60", "68")):
        return ".SH"
    elif stock_code.startswith(("00", "30")):  # 002/003 前缀已被 00 覆盖
        return ".SZ"
    elif stock_code.startswith(("8", "4")):
        return ".BJ"
    return ".SH"
```

**3b. `_clean_header` 删重复导入（177-182 行）**：

```python
def _clean_header(h: str) -> str:
    """清洗表头：去除单位括号"""
    h = str(h).strip()
    h = re.sub(r'[（(]单位[：:][^)）]*[)）]', '', h)  # 复用模块级 re（第 7 行已导入）
    return h
```

**3c. performance 维度阻塞调用包 executor（714-716 行，在 `generate_report_stream` 内）**：

```python
            # performance 维度：基于 OHLCV 自行计算全部技术指标
            # _enrich_performance 内含东财同步 HTTP，必须丢线程池避免阻塞事件循环
            if dim["key"] == "performance":
                text = await loop.run_in_executor(
                    None, _enrich_performance, text, stock_code
                )
```

**3d. 股票名提取同样包 executor（753 行）**：

```python
    # 组装完整 Markdown 报告（保留，供投研报告使用）
    # _extract_stock_name 兜底走东财同步 HTTP，同样丢线程池
    stock_name = await loop.run_in_executor(
        None, _extract_stock_name, raws.get("summary"), stock_code
    )
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd D:/karensAgent/backend && python -m pytest tests/test_report_unit.py -v`
Expected: 4 个全 PASS。

- [ ] **Step 5: 回归 SSE 链路**

Run: `cd D:/karensAgent/backend && python -m pytest tests/test_stock_api.py -v`
Expected: PASS。若环境允许，再手动起服务 `python -m uvicorn main:app`，前端触发一次 `/stock/skill/report` SSE，确认 performance 维度进度事件正常、complete 事件含 stock_name。（无法起服务则以单测 + review 为准，并在执行记录中注明。）

- [ ] **Step 6: 提交**

```bash
cd D:/karensAgent && git add backend/stock_agent/skill/report.py backend/tests/test_report_unit.py
git commit -m "fix(stock_agent): 报告流阻塞 HTTP 移入线程池，港股后缀误用快速失败"
```

---

## Task 8: skill/indicators.py — 删死代码 + 窗口函数 None 防御

**Files:**
- Modify: `backend/stock_agent/skill/indicators.py:12-31,71-89,118-155`
- Test: `backend/tests/test_indicators.py`（新建）

**Interfaces:**
- Produces: 各 `_calc_*` 签名不变。输入契约写入 docstring：`closes` 序列不允许含 None（两个数据源均满足）；`highs`/`lows` 可含 None（由 `_calc_kdj` 内部回退）。

**设计取舍（为什么不照审查工具给所有函数加 None 守卫）：** `_calc_ema`/`_calc_rsi` 是递推式计算，None 的防御语义模糊（跳过？继承前值？重新播种？），强行加守卫容易引入计算错误；而当前两个数据源（东财 `float()` 解析、iFinD 表格解析）产出的 `closes` 都不含 None。故只对语义明确的窗口函数（MA/BOLL）做防御，递推函数用 docstring 契约约束 + KDJ 保持既有 None 回退。

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_indicators.py`：

```python
"""技术指标计算测试

测试目标:
  1. 窗口函数（MA/BOLL）对 None 缺口不抛 TypeError
  2. 全 None 窗口返回 None 而不是崩溃
  3. 正常数据结果正确性不受防御逻辑影响
"""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))


def test_calc_ma_normal():
    from stock_agent.skill.indicators import _calc_ma
    out = _calc_ma([1.0, 2.0, 3.0, 4.0, 5.0], 3)
    assert out[:2] == [None, None]
    assert out[2] == 2.0
    assert out[4] == 4.0


def test_calc_ma_with_none_gap():
    """价格序列含 None 缺口时窗口取有效值平均，不抛 TypeError"""
    from stock_agent.skill.indicators import _calc_ma
    out = _calc_ma([1.0, None, 3.0, 4.0, 5.0], 3)
    assert len(out) == 5
    # 窗口 [None, 3.0, 4.0] → 有效值平均 3.5
    assert out[3] == 3.5
    # 窗口 [3.0, 4.0, 5.0] → 4.0
    assert out[4] == 4.0


def test_calc_ma_all_none_window():
    from stock_agent.skill.indicators import _calc_ma
    out = _calc_ma([None, None, None], 2)
    assert out == [None, None, None]


def test_calc_boll_with_none_gap():
    """BOLL 窗口含 None 时不崩，有效值不足时该点为 None"""
    from stock_agent.skill.indicators import _calc_boll
    closes = [10.0, None, 10.5, 11.0, 10.8, 10.9, 11.1, 10.7,
              10.6, 10.8, 11.0, 10.9, 10.8, 11.2, 11.3, 11.1,
              10.9, 10.8, 11.0, 11.1]
    out = _calc_boll(closes, 20)
    assert len(out["upper"]) == 20
    assert out["middle"][19] is not None  # 末点窗口有效值足够


def test_calc_kdj_none_fallback_unchanged():
    """KDJ 对 highs/lows 含 None 的回退行为保持原样"""
    from stock_agent.skill.indicators import _calc_kdj
    closes = [float(10 + i % 3) for i in range(15)]
    highs = [c + 0.5 if i % 4 else None for i, c in enumerate(closes)]
    lows = [c - 0.5 if i % 5 else None for i, c in enumerate(closes)]
    out = _calc_kdj(highs, lows, closes, 9)
    assert out["k"][14] is not None
    assert out["d"][14] is not None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd D:/karensAgent/backend && python -m pytest tests/test_indicators.py -v`
Expected: `test_calc_ma_with_none_gap`、`test_calc_boll_with_none_gap` FAIL（`TypeError: unsupported operand type(s) for +: 'float' and 'NoneType'`），其余 PASS。

- [ ] **Step 3: 最小实现**

修改 `backend/stock_agent/skill/indicators.py`：

**3a. `_calc_ma`（24-31 行）**：

```python
def _calc_ma(data: list, period: int) -> list:
    """计算简单移动平均（MA），返回与输入等长的列表

    窗口内 None 值被跳过，按有效值取平均；窗口全 None 则该点为 None。
    """
    if len(data) < period:
        return [None] * len(data)
    result = [None] * len(data)
    for i in range(period - 1, len(data)):
        window = [x for x in data[i - period + 1:i + 1] if x is not None]
        if window:
            result[i] = sum(window) / len(window)
    return result
```

**3b. `_calc_boll` 窗口方差防御（71-89 行）**：

```python
def _calc_boll(closes: list, period: int = 20, multiplier: float = 2.0) -> dict:
    """计算 BOLL 布林线

    Returns:
        {'upper': [...], 'middle': [...], 'lower': [...]}
    窗口内 None 值跳过；有效值不足 2 个时该点三轨为 None。
    """
    middle = _calc_ma(closes, period)
    upper = [None] * len(closes)
    lower = [None] * len(closes)

    for i in range(period - 1, len(closes)):
        mean = middle[i]
        if mean is None:
            continue
        window = [x for x in closes[i - period + 1:i + 1] if x is not None]
        if len(window) < 2:
            continue
        variance = sum((x - mean) ** 2 for x in window) / len(window)
        std = math.sqrt(variance)
        upper[i] = mean + multiplier * std
        lower[i] = mean - multiplier * std

    return {'upper': upper, 'middle': middle, 'lower': lower}
```

**3c. `_calc_kdj` 删死代码（136-137 行）**：

```python
    for i in range(n - 1, length):
        # 窗口内的最高/最低（highs/lows 含 None 时回退用 close 近似）
        win_high = max((highs[j] if highs[j] is not None else closes[j]) for j in range(i - n + 1, i + 1))
        win_low = min((lows[j] if lows[j] is not None else closes[j]) for j in range(i - n + 1, i + 1))
```

（删除原 136-137 行计算后从未使用的 `hi`、`lo` 两行。）

**3d. `_calc_ema`/`_calc_rsi`/`_calc_macd` docstring 补输入契约**（各函数 docstring 首行后加一行）：

```python
    """计算指数移动平均（EMA），返回与输入等长的列表，首段不足时为 None

    输入契约：data 不允许含 None（当前东财/iFinD 两个数据源均满足）。
    """
```

（`_calc_rsi` 同理加"输入契约：closes 不允许含 None"；`_calc_macd` 加"经由 _calc_ema 继承该契约"。）

- [ ] **Step 4: 运行测试确认通过**

Run: `cd D:/karensAgent/backend && python -m pytest tests/test_indicators.py -v`
Expected: 5 个全 PASS。

- [ ] **Step 5: 提交**

```bash
cd D:/karensAgent && git add backend/stock_agent/skill/indicators.py backend/tests/test_indicators.py
git commit -m "fix(stock_agent): 指标窗口函数 None 防御，删除 KDJ 死代码，补充输入契约"
```

---

## Task 9: models.py — 类型安全（数值兼容 + 0 值保留）+ 清理

**Files:**
- Modify: `backend/stock_agent/models.py:10,33-41,284-291,429-438,445-457`
- Test: `backend/tests/test_models.py`（追加）

**Interfaces:**
- Produces: `_iter_fields()` yield 值统一为 `str`（与 `_lookup: dict[str, str]` 标注一致）；`_first_of()` 返回 `str`。领域类目前无生产调用方，改动不影响前端。

- [ ] **Step 1: 写失败测试**

在 `backend/tests/test_models.py` 末尾追加（该文件现有测试均用函数内 import 风格，保持一致）：

```python
def test_iter_fields_numeric_and_zero():
    """iFind 可能返回数值型：不抛 AttributeError，且合法 0 值不得丢弃"""
    from stock_agent.models import _iter_fields

    records = [{
        "毛利率": 89.76,        # float
        "营收增速": 0,           # 合法零值，必须保留
        "净利润": 0.0,           # 合法零值，必须保留
        "空串": "",             # 空值丢弃
        "空值": None,           # None 丢弃
        "证券代码": "600519",    # 元数据列跳过
    }]
    fields = dict(_iter_fields(records))
    assert fields["毛利率"] == "89.76"
    assert fields["营收增速"] == "0"
    assert fields["净利润"] == "0.0"
    assert "空串" not in fields
    assert "空值" not in fields
    assert "证券代码" not in fields


def test_first_of_numeric_value():
    """_first_of 对数值型字段应安全转 str 返回"""
    from stock_agent.models import NewsEventsData

    record = {"日期": 20260717, "资讯标题": "测试标题"}
    time_val = NewsEventsData._first_of(record, "日期", "time")
    assert time_val == "20260717"
    # 0 值也算非空
    record2 = {"date": 0}
    assert NewsEventsData._first_of(record2, "date") == "0"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd D:/karensAgent/backend && python -m pytest tests/test_models.py::test_iter_fields_numeric_and_zero tests/test_models.py::test_first_of_numeric_value -v`
Expected: FAIL（`AttributeError: 'float' object has no attribute 'strip'`；`0` 被 falsy 丢弃）。

- [ ] **Step 3: 最小实现**

修改 `backend/stock_agent/models.py`：

**3a. 删无用导入（第 10 行）**：

```python
from typing import Optional
```

**3b. `_iter_fields`（33-41 行）**：

```python
def _iter_fields(records: list[dict], skip_meta: bool = True):
    """遍历 records 列表的所有 key-value，跳过元数据列和空值

    值统一转 str 输出（iFind 可能返回 int/float）；
    判空基于转换后的字符串，故数值 0 / 0.0 作为合法金融数据保留。
    """
    for r in records:
        for k, v in r.items():
            if skip_meta and k in _TABLE_META_KEYS:
                continue
            s = "" if v is None else str(v).strip()
            if not s:
                continue
            yield k, s
```

**3c. `_first_of`（284-291 行）**：

```python
    @staticmethod
    def _first_of(record: dict, *keys: str) -> str:
        """从 record 中取第一个非空字段值（兼容非字符串类型，统一转 str）"""
        for k in keys:
            val = record.get(k, "")
            s = "" if val is None else str(val).strip()
            if s:
                return s
        return ""
```

**3d. `MarketEnvData.to_prompt_context`（434-438 行区域）**：

```python
            for k, v in r.items():
                if k in ("name", "code") or k in _TABLE_META_KEYS:
                    continue
                s = "" if v is None else str(v).strip()  # 数值安全 + 0 值保留
                if s:
                    lines.append(f"- {k}：{s}")
```

**3e. `MarketEnvData.to_frontend`（452-456 行区域）**：

```python
            for k, v in r.items():
                if k in ("name", "code") or k in _TABLE_META_KEYS:
                    continue
                s = "" if v is None else str(v).strip()
                if s:
                    fields.append({"name": k, "value": s, "unit": ""})
```

**3f. `ShareholderData.to_prompt_context` 硬编码字段加观察注释（232-236 行区域，不改逻辑）**：

```python
        # 前十大股东
        # NOTE: 字段名是同花顺官方约定（含第{rank}名排名模板），非随意硬编码；
        # 若 iFind 改版字段命名导致取数静默为空，考虑按模式匹配做动态发现
        lines.append("\n**前十大股东**：")
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd D:/karensAgent/backend && python -m pytest tests/test_models.py -v`
Expected: 全部 PASS（既有 12 个 + 新增 2 个）。

- [ ] **Step 5: 提交**

```bash
cd D:/karensAgent && git add backend/stock_agent/models.py backend/tests/test_models.py
git commit -m "fix(stock_agent): models 值处理兼容数值类型并保留合法零值，删除无用导入"
```

---

## Task 10: analyze.py — JSON 提取改括号深度匹配（替代贪婪正则）

**Files:**
- Modify: `backend/stock_agent/analyze.py:340-345`（策略 3），新增模块级辅助函数
- Test: `backend/tests/test_analyze.py`（追加）

**Interfaces:**
- Produces: `_parse_json(raw_text, max_retries=2) -> dict` 签名不变。新增 `_extract_outermost_json(text) -> str | None`。
- 注意：审查工具建议的非贪婪 `\{.*?\}` 对嵌套 JSON 是错的（9 模块 JSON 必然多层嵌套，非贪婪会在第一个内层 `}` 截断）。正确方案是括号深度匹配 + 字符串状态机。

- [ ] **Step 1: 写失败测试**

在 `backend/tests/test_analyze.py` 追加：

```python
def test_parse_json_with_surrounding_prose():
    """JSON 前后夹杂说明文字时，应提取最外层完整 JSON（贪婪正则会在跨多对象时越界）"""
    from stock_agent.analyze import _parse_json

    raw = '分析结果如下 {"score": 85, "nested": {"a": 1}, "list": [1, 2]} 以上。'
    report = _parse_json(raw)
    assert report["score"] == 85
    assert report["nested"]["a"] == 1
    assert report["list"] == [1, 2]


def test_parse_json_braces_inside_string():
    """字符串内的大括号不应干扰深度匹配"""
    from stock_agent.analyze import _parse_json

    raw = '{"desc": "比例 {x/y} 说明", "score": 60}'
    report = _parse_json(raw)
    assert report["score"] == 60
    assert "{x/y}" in report["desc"]


def test_parse_json_two_blocks_takes_first_complete():
    """前后两个 JSON 块时，取第一个完整的（贪婪正则会合并两块导致解析失败）"""
    from stock_agent.analyze import _parse_json

    raw = '前言 {"score": 70} 中间干扰 {"other": 1} 结尾'
    report = _parse_json(raw)
    assert report["score"] == 70


def test_extract_outermost_json_helper():
    from stock_agent.analyze import _extract_outermost_json

    assert _extract_outermost_json('xx {"a": {"b": 1}} yy') == '{"a": {"b": 1}}'
    assert _extract_outermost_json('没有 JSON') is None
    assert _extract_outermost_json('{"未闭合": 1') is None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd D:/karensAgent/backend && python -m pytest tests/test_analyze.py -k "parse_json or outermost" -v`
Expected: FAIL（`_extract_outermost_json` 不存在；`test_parse_json_two_blocks_takes_first_complete` 在当前贪婪正则下提取出 `{"score": 70} 中间干扰 {"other": 1}` 导致解析失败抛异常）。

- [ ] **Step 3: 最小实现**

在 `backend/stock_agent/analyze.py` 的 `_parse_json` 函数**之前**新增：

```python
def _extract_outermost_json(text: str) -> str | None:
    """按括号深度匹配提取最外层完整 {...}（比贪婪/非贪婪正则都稳健）

    - 跟踪字符串内外状态，字符串内的大括号不参与配对
    - 返回第一个深度归零的完整 JSON 子串；找不到返回 None
    """
    start = text.find('{')
    if start == -1:
        return None
    depth = 0
    in_string = False
    escaped = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == '\\':
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None
```

修改 `_parse_json` 策略 3（340-345 行）：

```python
            # 策略 3：JSON 前后可能有文字，按括号深度匹配提取最外层完整 {...}
            extracted = _extract_outermost_json(text)
            if extracted and extracted != text:
                text = extracted
                print(f"[analyze] → 已提取最外层 JSON", file=sys.stderr)
                continue
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd D:/karensAgent/backend && python -m pytest tests/test_analyze.py -v`
Expected: 全部 PASS。

- [ ] **Step 5: 提交**

```bash
cd D:/karensAgent && git add backend/stock_agent/analyze.py backend/tests/test_analyze.py
git commit -m "fix(stock_agent): LLM 输出 JSON 提取改用括号深度匹配替代贪婪正则"
```

---

## Task 11: SSL 证书校验启用（security high，⚠️ 需王磊哥哥批准后执行）

**前置条件：王磊哥哥明确同意修改全局 skill 文件 `~/.claude/skills/ifind-finance-data/call.py`。**

**可行性依据（已验证，非猜测）：** `backend/tests/probe_results/ssl_probe_20260710_224140.json` 的实验结论——iFinD 证书为 DigiCert/GeoTrust 签发的 `*.51ifind.com` 通配符证书（有效期至 2026-12-17）；**`verify=True` 连接成功（status 200）**；`certifi` CA bundle 可用；探针官方建议 `use_certifi`。

**风险提示：**
- `call.py` 位于 `~/.claude/skills/`，是**用户级共享 skill**，其他 agent/项目也在用。改 `verify=True` 影响全局（探针证明可行，风险低）。
- 证书 2026-12-17 到期后若同花顺换证异常，校验会失败——届时是安全机制正常生效，而非 bug。
- `D:\karensAgent\.claude\ifind_mcp说明书\call.py` 是文档镜像副本，一并同步以免日后对照困惑。

**Files:**
- Modify: `~/.claude/skills/ifind-finance-data/call.py:41,82`
- Modify: `backend/stock_agent/skill/__init__.py:11-13`
- Modify: `D:/karensAgent/.claude/ifind_mcp说明书/call.py`（镜像同步）

- [ ] **Step 1: 重跑 SSL 探针刺探当前证书状态**

Run: `cd D:/karensAgent/backend && python tests/probe_ifind_ssl.py`
Expected: `verify=True: ✅ status=200`，证书剩余天数为正。若证书已过期/更换导致 verify=True 失败，**停止本任务**并报告王磊哥哥。

- [ ] **Step 2: 修改 call.py 两处 verify**

`~/.claude/skills/ifind-finance-data/call.py` 第 41、82 行：

```python
        verify=True,  # 启用 TLS 证书校验（iFinD 为 DigiCert 签发证书，ssl_probe 实验已验证可行）
```

同步修改 `D:/karensAgent/.claude/ifind_mcp说明书/call.py` 的对应两处。

- [ ] **Step 3: 移除 skill/__init__.py 的警告压制**

`backend/stock_agent/skill/__init__.py:11-13`：

```python
# 历史遗留：call.py 曾用 verify=False 并在此压制 SSL 警告。
# 2026-07-29 已启用证书校验（verify=True），警告压制随之移除。
```

（删除 `warnings.filterwarnings("ignore", message="Unverified HTTPS request")` 一行；若 `import warnings` 从此无人使用则一并删除。）

- [ ] **Step 4: 端到端验证**

Run:
```bash
cd D:/karensAgent/backend && python -c "
import sys; sys.path.insert(0, '.')
from stock_agent.skill import call_skill, extract_text
r = call_skill('stock', 'get_stock_summary', {'query': '股票代码600519的基本信息'})
print('ok=', r.get('ok'))
text = extract_text(r)
print('数据可用=', '茅台' in text or '公司' in text)
"
```
Expected: `ok= True`，`数据可用= True`，且**无任何 SSL 警告输出**。

- [ ] **Step 5: 回归全部测试 + 提交**

Run: `cd D:/karensAgent/backend && python -m pytest tests/test_skill_extract.py tests/test_analyze.py tests/test_render.py tests/test_models.py tests/test_eastmoney.py tests/test_indicators.py tests/test_report_unit.py -v`
Expected: PASS。

```bash
cd D:/karensAgent && git add backend/stock_agent/skill/__init__.py .claude/ifind_mcp说明书/call.py
git commit -m "fix(stock_agent): 启用 iFinD API TLS 证书校验，移除 SSL 警告压制"
```

（`~/.claude/skills/` 不在本仓库内，无需 git 跟踪；执行记录中注明已改。）

---

## Task 12: 全量回归 + 执行总结

**Files:** 无新增修改。

- [ ] **Step 1: 跑全量相关测试**

Run: `cd D:/karensAgent/backend && python -m pytest tests/test_analyze.py tests/test_render.py tests/test_models.py tests/test_skill_extract.py tests/test_eastmoney.py tests/test_indicators.py tests/test_report_unit.py tests/test_stock_api.py -v`
Expected: 全 PASS。

- [ ] **Step 2: 确认临时探针已清理**

Run: `ls D:/karensAgent/backend/tests/probe_code_convention.py`
Expected: 文件不存在（Task 2 已删）。

- [ ] **Step 3: 端到端冒烟（环境允许时）**

Run: `cd D:/karensAgent/backend && python -m stock_agent.analyze 600398`
Expected: 完整报告输出，stderr 诊断日志只含 `key_len=`，报告页脚含 Token 消耗，`reports/` 下生成 md 文件。

- [ ] **Step 4: 向王磊哥哥汇报**

输出执行总结：各 Task 完成情况、Task 2 验证记录表、Task 11 是否执行、测试通过数、遗留观察项（ShareholderData 硬编码、push_to_feishu 未来并发时的 executor 包装）。

---

## 自检记录（Self-Review）

1. **Spec 覆盖**：1.txt 共 20 条问题——A 类 9 条（Task 1/3/4/5/6/7/10）、B 类 1 条（Task 2→3）、C 类 5 条（Task 5/6/7/8/9）、D 类 3 条（Task 3/7/9）、E 类不修 3 条（均附理由）、待决策 1 条（usage 参数，默认方案已入 Task 4）。无遗漏。
2. **占位符扫描**：除 Task 2 的"验证记录表"（需执行时实测填写，属验证任务的正当产出）外，无 TBD/TODO 式占位；所有代码步骤均含完整代码块。
3. **类型一致性**：`_escape_cell(value) -> str`（Task 4）、`_extract_outermost_json(text) -> str | None`（Task 10）、`_iter_fields` yield `(str, str)`（Task 9）在各任务内定义与使用一致；`push_to_feishu(md_report, stock_name, stock_code)` 签名在 Task 5 与 stock_api.py:323 既有正确调用一致。
