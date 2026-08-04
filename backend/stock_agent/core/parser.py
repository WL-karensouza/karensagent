"""LLM 输出 JSON 容错解析 — DeepSeek Reasoner 偶发非法 JSON 的修复策略"""
import json
import sys
from datetime import datetime
from pathlib import Path


def _dump_parse_failure(raw_text: str, fail_dir: Path | None = None) -> None:
    """解析失败传播前落盘原文 — 容错策略持续回放的语料（tech-tracker #2）

    语料目录：stock_agent/reports/failures/（已加入 .gitignore，不进版本库）。
    回放工具：tests/replay_failures.py。落盘动作全程吞异常，绝不影响主流程。
    """
    try:
        target_dir = fail_dir or Path(__file__).resolve().parent.parent / "reports" / "failures"
        target_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_file = target_dir / f"{ts}_{abs(hash(raw_text)) % 100000:05d}.txt"
        out_file.write_text(raw_text or "<empty>", encoding="utf-8")
        print(f"[analyze] 💾 解析失败语料已存: {out_file}", file=sys.stderr)
    except Exception as e:
        print(f"[analyze] ⚠️ 语料落盘失败（不影响主流程）: {e}", file=sys.stderr)


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


def _bracket_completion_suffix(text: str) -> str:
    """栈扫描未闭合括号（跳过字符串内部），返回逆序补全后缀

    如 '{"a": [{"b": 1' → 栈 ['{','[','{'] → 后缀 '}]}'.
    旧的简单计数补全（先 ] 后 }）无视嵌套顺序，会把 signal_attribution 这类
    "数组内嵌对象"结构补成无效序列——截断救援在深层位置全灭的根因。
    """
    stack = []
    in_string = False
    escaped = False
    for ch in text:
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
        elif ch in '{[':
            stack.append(ch)
        elif ch == '}' and stack and stack[-1] == '{':
            stack.pop()
        elif ch == ']' and stack and stack[-1] == '[':
            stack.pop()
    return ''.join('}' if c == '{' else ']' for c in reversed(stack))


def _parse_json(raw_text: str, max_retries: int = 3) -> dict:
    """容错 JSON 解析 — DeepSeek Reasoner 偶尔输出非法 JSON

    常见问题及修复策略（按序）：
      1. 字符串内未转义控制字符（如裸换行）→ 默认宽松模式 strict=False 永久免疫
      2. 未闭合字符串（截断在字符串内部）→ 先闭合字符串，再交给括号补全
      3. 尾随逗号（"key": "val",}）→ 移除
      4. 字符串内未转义裸引号 → 启发式转义错误位置前的可疑引号
      5. 末尾截断（finish_reason=length）→ 按栈逆序补全缺失括号
      6. JSON 前后夹杂文字 → 提取最外层 {...}
    """
    import re as _re

    text = raw_text

    for attempt in range(max_retries + 1):
        try:
            # 默认宽松模式：允许字符串内未转义控制字符（DeepSeek 偶发裸换行），对合法 JSON 无任何副作用
            return json.loads(text, strict=False)
        except json.JSONDecodeError as e:
            if attempt >= max_retries:
                raise  # 重试耗尽，抛出原始错误

            print(f"[analyze] ⚠️ JSON 解析失败 (尝试 {attempt+1}/{max_retries+1}): {e}", file=sys.stderr)
            err_msg = str(e)

            # 策略 1：未闭合字符串（截断在字符串内部）→ 先闭合，再交给后续策略
            # 必须先于括号计数：未闭合字符串内部的括号会污染括号计数
            if "Unterminated string" in err_msg:
                stripped = text.rstrip()
                if stripped.endswith(','):
                    stripped = stripped[:-1]
                # 末尾若是悬空转义符（奇数个 \），补的引号会被转义 → 先删掉
                n_slash = len(stripped) - len(stripped.rstrip('\\'))
                if n_slash % 2 == 1:
                    stripped = stripped[:-1]
                text = stripped + '"'
                print(f"[analyze] → 已闭合未闭合字符串", file=sys.stderr)
                continue

            # 策略 2：尾随逗号 — 删除 , 后紧跟 } 或 ] 的模式
            # （"Expecting property name" 是 CPython 对尾随逗号的实际报错文案）
            if "trailing comma" in err_msg.lower() or "Expecting ',' delimiter" in err_msg or "Expecting value" in err_msg or "Expecting property name" in err_msg:
                fixed = _re.sub(r',(\s*[}\]])', r'\1', text)
                if fixed != text:
                    text = fixed
                    print(f"[analyze] → 已移除尾随逗号", file=sys.stderr)
                    continue

            # 策略 3：字符串内未转义裸引号（LLM 常见缺陷，如"所谓"陷阱""）
            # 解析器把裸引号当字符串收尾、其后正文当成 key/非法 token → 报 Expecting ':'/',' delimiter
            # 错误位置在文本内部才处理（截断型错误在文末，留给策略 4 括号补全，防 regress）
            # 启发式：转义错误位置前的可疑引号重试，重试上限天然兜底防误伤循环
            if "Expecting ':' delimiter" in err_msg or "Expecting ',' delimiter" in err_msg:
                m = _re.search(r'\(char (\d+)\)', err_msg)
                if m and int(m.group(1)) < len(text.rstrip()) - 1:
                    z = int(m.group(1))
                    q = text.rfind('"', 0, z)
                    if "Expecting ':' delimiter" in err_msg:
                        # 解析器把"伪 key"当成了 key：伪 key 本身带引号，要转义其开引号（回退两次）
                        q = text.rfind('"', 0, q)
                    if q != -1 and text[q - 1:q] != '\\':
                        text = text[:q] + '\\"' + text[q + 1:]
                        print(f"[analyze] → 已转义可疑裸引号（位置 {q}）", file=sys.stderr)
                        continue

            # 策略 4：截断 — 按栈逆序补全未闭合括号（尊重嵌套顺序）
            suffix = _bracket_completion_suffix(text)
            if suffix:
                text = text.rstrip()
                if text.endswith(','):
                    text = text[:-1]  # 移除末尾逗号再补
                text += suffix
                print(f"[analyze] → 已补全括号: {suffix}", file=sys.stderr)
                continue

            # 策略 5：JSON 前后可能有文字，按括号深度匹配提取最外层完整 {...}
            extracted = _extract_outermost_json(text)
            if extracted and extracted != text:
                text = extracted
                print(f"[analyze] → 已提取最外层 JSON", file=sys.stderr)
                continue

            raise  # 以上策略都不匹配，抛原始错误
