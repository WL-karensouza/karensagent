"""
TDD Step 5: analyze.py 测试（适配 2026-07-16 9 模块 Prompt）

测试目标:
  1. build_system_prompt — 三层 prompt 组装
  2. build_user_prompt — 包装 Markdown 数据报告
  3. analyze — 调用 deepseek-v4-flash（验证 model 参数）
  4. 数据不完整时的拒绝逻辑
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(Path(__file__).parent))  # tests 目录自身：供 test_validator 等同级测试模块导入


# ═══════════════════════════════════════════
# System Prompt 构建
# ═══════════════════════════════════════════

def test_build_system_prompt_structure():
    """system prompt 应包含：角色定义 + 核心原则 + 输出 Schema（三层）"""
    from stock_agent.analyze import build_system_prompt

    prompt = build_system_prompt()

    # 1. 角色定义（Layer 1）
    assert "投资顾问" in prompt or "分析" in prompt, "应包含角色定义"

    # 2. 三步思考链
    assert "三步思考链" in prompt or "数据事实化" in prompt, "应包含三步思考链"

    # 3. 9 个模块
    assert "核心结论" in prompt
    assert "公司画像" in prompt
    assert "财务健康" in prompt
    assert "股价走势" in prompt
    assert "北向资金" in prompt
    assert "股东结构" in prompt or "股东筹码" in prompt
    assert "催化剂" in prompt
    assert "风险评估" in prompt
    assert "操作指南" in prompt

    # 4. 核心原则（Layer 2）
    assert "基于数据" in prompt or "不编造" in prompt or "数据支撑" in prompt

    # 5. 术语禁令
    assert "戴维斯双击" in prompt or "术语" in prompt

    # 6. 输出 JSON Schema（Layer 3）
    assert "score" in prompt
    assert "signal_attribution" in prompt
    assert "JSON" in prompt

    print(f"[OK] build_system_prompt: {len(prompt)} chars")


def test_build_system_prompt_has_modules():
    """system prompt 应明确列出 9 个分析模块"""
    from stock_agent.analyze import build_system_prompt

    prompt = build_system_prompt()

    # 模块标题验证
    module_titles = [
        "核心结论与操作建议",
        "公司画像与估值定位",
        "财务健康状况",
        "股价走势与资金动向",
        "北向资金",
        "股东结构与筹码集中度",
        "催化剂与近期舆情",
        "风险评估与 ESG",
        "散户实战操作指南",
    ]
    for title in module_titles:
        assert title in prompt, f"缺少模块: {title}"

    print("[OK] 9 个模块全部存在于 system prompt 中")


# ═══════════════════════════════════════════
# User Prompt 构建
# ═══════════════════════════════════════════

def test_build_user_prompt():
    """user prompt 应包装 Markdown 数据报告"""
    from stock_agent.analyze import build_user_prompt

    markdown_report = "# 600519 贵州茅台 数据报告\n\n## 实时行情\n收盘价：1800.00元\n"
    prompt = build_user_prompt(markdown_report)

    assert "600519" in prompt
    assert "1800.00" in prompt
    assert "iFinD" in prompt or "同花顺" in prompt

    print(f"[OK] build_user_prompt: {len(prompt)} chars")


def test_build_user_prompt_empty():
    """空报告不应崩溃"""
    from stock_agent.analyze import build_user_prompt

    prompt = build_user_prompt("")
    assert len(prompt) > 0  # 至少包含导语
    print(f"[OK] build_user_prompt 空输入: {len(prompt)} chars")


# ═══════════════════════════════════════════
# LLM 调用
# ═══════════════════════════════════════════

def test_analyze_uses_reasoner_model():
    """analyze() 应使用 deepseek-v4-flash 模型"""
    from stock_agent.analyze import analyze

    markdown_report = "# 测试数据报告\n内容..."

    with patch('stock_agent.analyze.OpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        mock_completion = MagicMock()
        mock_choice = MagicMock()
        # 新 9 模块 JSON 格式
        mock_choice.message.content = (
            '{"score":75,"decision":"看多",'
            '"module_1_核心结论":{"rating_sentence":"测试结论","core_logic":[],"reference_prices":{}}'
            '}'
        )
        mock_completion.choices = [mock_choice]
        mock_completion.usage.prompt_tokens = 500
        mock_completion.usage.completion_tokens = 200
        mock_completion.usage.total_tokens = 700
        mock_client.chat.completions.create.return_value = mock_completion

        report, usage = analyze(markdown_report)

        # 验证调用了 deepseek-v4-flash 且显式开启思考模式
        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs[1]["model"] == "deepseek-v4-flash", (
            f"应使用 deepseek-v4-flash，实际: {call_kwargs[1]['model']}"
        )
        assert call_kwargs[1]["extra_body"] == {"thinking": {"type": "enabled"}}, (
            f"应显式开启思考模式，实际: {call_kwargs[1].get('extra_body')}"
        )
        assert call_kwargs[1].get("reasoning_effort") == "high", (
            f"思考强度应为 high，实际: {call_kwargs[1].get('reasoning_effort')}"
        )
        assert report["score"] == 75
        assert report["decision"] == "看多"
        assert "module_1_核心结论" in report
        assert usage["total"] == 700

        print(f"[OK] analyze 使用 deepseek-v4-flash, score={report['score']}")


def test_analyze_validates_data():
    """analyze() 应在数据报告为空时拒绝调用 LLM"""
    from stock_agent.analyze import analyze
    from stock_agent.models import DataIncompleteError

    try:
        analyze("")
        assert False, "应抛出 DataIncompleteError"
    except DataIncompleteError:
        pass  # 预期行为
    print("[OK] analyze 数据守卫：空报告时抛出 DataIncompleteError")


def test_analyze_validates_whitespace():
    """analyze() 应在数据报告仅含空白时拒绝"""
    from stock_agent.analyze import analyze
    from stock_agent.models import DataIncompleteError

    try:
        analyze("   \n  \t  ")
        assert False, "应抛出 DataIncompleteError"
    except DataIncompleteError:
        pass
    print("[OK] analyze 数据守卫：空白报告时抛出 DataIncompleteError")


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


# ═══════════════════════════════════════════
# JSON 提取 — 括号深度匹配（替代贪婪正则）
# ═══════════════════════════════════════════

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


def test_parse_json_invalid_control_character():
    """字符串内含裸换行（未转义控制字符）→ 宽松模式解析（E2 实验 000938 挖出的真实缺陷）"""
    from stock_agent.analyze import _parse_json

    raw = '{"score": 70, "desc": "第一行\n第二行"}'  # 字符串内是真实换行符，严格模式必炸
    report = _parse_json(raw)
    assert report["score"] == 70
    assert "第一行" in report["desc"] and "第二行" in report["desc"]
    print("[OK] _parse_json 宽松模式：字符串裸控制字符")


def test_parse_json_unterminated_string():
    """截断在字符串内部（Unterminated string）→ 闭合字符串 + 补全括号（E2 实验真实故障）"""
    from stock_agent.analyze import _parse_json

    # 模拟 finish_reason=length 截断：desc 字符串写到一半被切断
    raw = '{"score": 70, "decision": "看多", "desc": "这段分析写到一半被截'
    report = _parse_json(raw)
    assert report["score"] == 70
    assert report["decision"] == "看多"
    assert "被截" in report["desc"]  # 截断前的内容应保留
    print("[OK] 未闭合字符串：闭合 + 括号补全")


def test_parse_json_unterminated_string_in_array():
    """截断在数组内的字符串 → 闭合后括号补全，数组已闭合元素保留"""
    from stock_agent.analyze import _parse_json

    raw = '{"score": 60, "list": ["完整项", "半截'
    report = _parse_json(raw)
    assert report["score"] == 60
    assert report["list"] == ["完整项", "半截"]  # 闭合后半截项也保留
    print("[OK] 数组内未闭合字符串")


def test_parse_json_control_char_plus_trailing_comma():
    """复合故障：裸控制字符 + 尾随逗号 → 宽松模式 + 尾随逗号策略合力（E2 实验 300369 故障形态）"""
    from stock_agent.analyze import _parse_json

    raw = '{"score": 55, "desc": "第一行\n第二行",}'  # 裸换行 + 尾随逗号
    report = _parse_json(raw)
    assert report["score"] == 55
    assert "第一行" in report["desc"]
    print("[OK] 复合故障：控制字符 + 尾随逗号")


def test_parse_json_nested_truncation_order():
    """截断在"数组内嵌对象"深层（signal_attribution 形态）→ 补全顺序必须 }]} 而非 ]}（突变回归挖出的潜伏 bug）"""
    from stock_agent.analyze import _parse_json

    # 截断在 signal_attribution 数组内的对象中间
    raw = '{"score": 66, "decision": "震荡", "signal_attribution": [{"source": "估值面", "weight": 0.2}, {"source": "财务面"'
    report = _parse_json(raw)
    assert report["score"] == 66
    assert report["signal_attribution"][0]["weight"] == 0.2  # 已闭合的元素完整保留
    print("[OK] 深层嵌套截断：栈逆序补全")


def test_parse_json_bare_quote_in_string():
    """字符串内未转义裸引号（LLM 常见缺陷）→ 启发式转义救回（突变回归 0/21 → 21/21 的关键修复）"""
    from stock_agent.analyze import _parse_json

    # desc 值里含两个未转义的裸引号，结构其余部分完好
    raw = '{"score": 70, "desc": "这就是所谓"裸引号"的情况", "decision": "看多"}'
    report = _parse_json(raw)
    assert report["score"] == 70
    assert report["decision"] == "看多"  # 裸引号之后的字段仍能救出
    print("[OK] 裸引号启发式转义")


def test_dump_parse_failure_saves_corpus(tmp_path):
    """解析最终失败时应落盘原文语料（tech-tracker #2，回放工具的输入）"""
    from stock_agent.analyze import _dump_parse_failure

    _dump_parse_failure('{"score": 坏了的 json', fail_dir=tmp_path)
    dumps = list(tmp_path.glob("*.txt"))
    assert len(dumps) == 1
    assert "坏了的 json" in dumps[0].read_text(encoding="utf-8")
    print("[OK] 失败语料落盘")


def test_extract_outermost_json_helper():
    from stock_agent.analyze import _extract_outermost_json

    assert _extract_outermost_json('xx {"a": {"b": 1}} yy') == '{"a": {"b": 1}}'
    assert _extract_outermost_json('没有 JSON') is None
    assert _extract_outermost_json('{"未闭合": 1') is None


# ═══════════════════════════════════════════
# E0 质量层：analyze_with_validation 校验 + 修正
# ═══════════════════════════════════════════

def _mock_completion(content: str, total: int = 700):
    """构造 mock LLM 响应（E0/E1 测试共用）"""
    mock_completion = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = content
    mock_choice.finish_reason = "stop"
    mock_completion.choices = [mock_choice]
    mock_completion.usage.prompt_tokens = 500
    mock_completion.usage.completion_tokens = 200
    mock_completion.usage.total_tokens = total
    return mock_completion


def test_analyze_passes_history_context_to_prompt():
    """analyze() 的 history_context 参数应透传进 user prompt（E1 注入链路）"""
    from stock_agent.analyze import analyze

    with patch('stock_agent.analyze.OpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_completion(
            '{"score":75,"decision":"看多"}'
        )

        analyze("# 测试报告\n有内容", history_context="HISTORY_MARKER_XYZ")

        messages = mock_client.chat.completions.create.call_args[1]["messages"]
        user_msg = messages[1]["content"]
        assert "HISTORY_MARKER_XYZ" in user_msg, "历史上下文应注入 user prompt"
        assert "module_1" in user_msg, "应附带对比引导语"
    print("[OK] analyze 历史上下文透传")


def test_analyze_with_validation_no_repair_when_valid():
    """报告一次合规 → 不触发修正调用"""
    import json as _json
    from stock_agent.analyze import analyze_with_validation
    from test_validator import make_valid_report

    with patch('stock_agent.analyze.OpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_completion(
            _json.dumps(make_valid_report(), ensure_ascii=False)
        )

        report, usage = analyze_with_validation("# 测试报告\n有内容")

        assert mock_client.chat.completions.create.call_count == 1, "合规报告只应调用一次"
        assert "_validation_issues" not in report
        assert usage["total"] == 700
    print("[OK] analyze_with_validation: 合规不修正")


def test_analyze_with_validation_repair_succeeds():
    """首次违规 + 修正后合规 → 采纳修正版，usage 累积"""
    import json as _json
    from stock_agent.analyze import analyze_with_validation
    from test_validator import make_valid_report

    bad = '{"score":75,"decision":"买入"}'  # 多违规：枚举错 + 缺 9 模块
    good = _json.dumps(make_valid_report(), ensure_ascii=False)

    with patch('stock_agent.analyze.OpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            _mock_completion(bad, total=700),
            _mock_completion(good, total=900),
        ]

        report, usage = analyze_with_validation("# 测试报告\n有内容")

        assert mock_client.chat.completions.create.call_count == 2, "主调用 + 修正调用"
        assert "_validation_issues" not in report
        assert report["score"] == 72, "应采纳修正版（make_valid_report 的 score）"
        assert usage["total"] == 1600, "usage 应累积修正调用成本 700+900"
    print("[OK] analyze_with_validation: 修正成功 + usage 累积")


def test_analyze_with_validation_repair_fails_keeps_original():
    """修正后仍违规 → 兜底保留原报告，附 _validation_issues，不阻塞"""
    from stock_agent.analyze import analyze_with_validation

    bad = '{"score":75,"decision":"买入"}'
    with patch('stock_agent.analyze.OpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            _mock_completion(bad),
            _mock_completion(bad),
        ]

        report, usage = analyze_with_validation("# 测试报告\n有内容")

        assert mock_client.chat.completions.create.call_count == 2
        assert "_validation_issues" in report
        assert len(report["_validation_issues"]) > 0
        assert usage["total"] == 1400
    print("[OK] analyze_with_validation: 修正失败兜底")


if __name__ == "__main__":
    print("=" * 50)
    print("TDD Step 5: analyze.py 测试 (v2 9模块)")
    print("=" * 50)

    print("\n── System Prompt ──")
    test_build_system_prompt_structure()
    test_build_system_prompt_has_modules()

    print("\n── User Prompt ──")
    test_build_user_prompt()
    test_build_user_prompt_empty()

    print("\n── LLM 调用 ──")
    test_analyze_uses_reasoner_model()
    test_analyze_validates_data()
    test_analyze_validates_whitespace()

    print("\n" + "=" * 50)
    print("[OK] All tests passed")
