"""
TDD Step 5: analyze.py 测试（适配 2026-07-16 9 模块 Prompt）

测试目标:
  1. build_system_prompt — 三层 prompt 组装
  2. build_user_prompt — 包装 Markdown 数据报告
  3. analyze — 调用 deepseek-reasoner（验证 model 参数）
  4. 数据不完整时的拒绝逻辑
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))


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
    """analyze() 应使用 deepseek-reasoner 模型"""
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

        # 验证调用了 deepseek-reasoner
        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs[1]["model"] == "deepseek-reasoner", (
            f"应使用 deepseek-reasoner，实际: {call_kwargs[1]['model']}"
        )
        assert report["score"] == 75
        assert report["decision"] == "看多"
        assert "module_1_核心结论" in report
        assert usage["total"] == 700

        print(f"[OK] analyze 使用 deepseek-reasoner, score={report['score']}")


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
