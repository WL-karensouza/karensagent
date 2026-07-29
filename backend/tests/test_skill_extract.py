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
