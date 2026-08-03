import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Windows 控制台 UTF-8 编码
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 将 backend 加入 path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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

os.environ.setdefault("DEEPSEEK_API_KEY", env_vars.get("DEEPSEEK_API_KEY", ""))
FEISHU_WEBHOOK_URL = env_vars.get("FEISHU_STOCK_WEBHOOK_URL", "")

from openai import OpenAI


# ═══════════════════════════════════════════
# 1. 数据采集（委托给新 fetcher 系统）
# ═══════════════════════════════════════════

from stock_agent.models import DataIncompleteError  # noqa: F401 — 从 models 统一导出


# ═══════════════════════════════════════════
# 2. Prompt 构建（委托给 prompts 包，三层拆分见 prompts/ 各文件）
# ═══════════════════════════════════════════

from stock_agent.prompts import build_system_prompt, build_user_prompt


# ═══════════════════════════════════════════
# 3. LLM 调用
# ═══════════════════════════════════════════

def analyze(markdown_report: str, history_context: str = "") -> tuple[dict, dict]:
    """调用 DeepSeek Reasoner 分析 SKILL 数据报告，返回 (report, usage)。

    Args:
        markdown_report: SKILL 生成的 Markdown 格式综合数据报告
        history_context: 历史报告骨架上下文（E1 历史对比，空串 = 不注入）
    """
    # 数据守卫：报告不能为空
    if not markdown_report or not markdown_report.strip():
        raise DataIncompleteError("数据报告为空，拒绝调用 LLM 以防止幻觉")

    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise RuntimeError("未设置 DEEPSEEK_API_KEY，请检查 .env 文件")

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    user_prompt = build_user_prompt(markdown_report, history_context)

    resp = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[
            {"role": "system", "content": build_system_prompt()},
            {"role": "user", "content": user_prompt},
        ],
        # 显式开启思考模式（官方文档：deepseek-reasoner/deepseek-chat 已下架，
        # 统一使用 deepseek-v4-flash，默认即开启思考且 effort=high，此处显式声明防回归）
        extra_body={"thinking": {"type": "enabled"}},
        reasoning_effort="high",
        max_tokens=16384,  # 思考模式需足够 token 给 reasoning + content
    )

    content = resp.choices[0].message.content
    reasoning_content = getattr(resp.choices[0].message, 'reasoning_content', None)
    # 诊断日志（安全：只记录 key 长度，禁止输出 key 内容，防止日志系统泄密）
    import sys as _sys
    print(f"[analyze] key_len={len(api_key)} sys_prompt_len={len(build_system_prompt())} user_prompt_len={len(user_prompt)}", file=_sys.stderr)
    print(f"[analyze] content_len={len(content) if content else 0} reasoning_len={len(reasoning_content) if reasoning_content else 0} finish_reason={resp.choices[0].finish_reason}", file=_sys.stderr)
    usage = {
        "prompt": resp.usage.prompt_tokens,
        "completion": resp.usage.completion_tokens,
        "total": resp.usage.total_tokens,
    }

    # 解析 JSON（reasoner 可能把输出全放到 reasoning_content，content 为空）
    raw_text = content or ""
    if not raw_text.strip() and reasoning_content:
        print(f"[analyze] ⚠️ content 为空，尝试从 reasoning_content 提取 JSON", file=_sys.stderr)
        raw_text = reasoning_content

    # 剥离 ```json ... ``` 包裹
    if "```json" in raw_text:
        raw_text = raw_text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in raw_text:
        raw_text = raw_text.split("```", 1)[1].split("```", 1)[0]

    raw_text = raw_text.strip()
    if not raw_text:
        _dump_parse_failure(f"<empty> reasoning_len={len(reasoning_content) if reasoning_content else 0}")
        raise RuntimeError(
            f"DeepSeek Reasoner 返回空内容 "
            f"(content_len={len(content) if content else 0}, "
            f"reasoning_len={len(reasoning_content) if reasoning_content else 0}, "
            f"finish_reason={resp.choices[0].finish_reason})"
        )

    try:
        report = _parse_json(raw_text)
    except Exception:
        _dump_parse_failure(raw_text)  # 容错耗尽前落语料，供 tests/replay_failures.py 回放
        raise

    # 结构门关：思考吃满输出上限、正文截断时，容错解析可能把思考文字里的
    # 草稿残片救成合法 dict（2026-08-04 偶发空报告事故形态）。
    # 坍塌按生成失败处理：上游整体重试，绝不作为合法报告存库。
    if is_collapsed_report(report):
        _dump_parse_failure(raw_text)
        raise StructuralCollapseError(
            f"LLM 输出结构坍塌（顶层仅字段 {list(report)[:5]}），判为截断残片",
            usage=usage,  # 带上成本，供上游重试时累积保持可观测
        )
    return report, usage


def _dump_parse_failure(raw_text: str, fail_dir: Path | None = None) -> None:
    """解析失败传播前落盘原文 — 容错策略持续回放的语料（tech-tracker #2）

    语料目录：stock_agent/reports/failures/（已加入 .gitignore，不进版本库）。
    回放工具：tests/replay_failures.py。落盘动作全程吞异常，绝不影响主流程。
    """
    try:
        target_dir = fail_dir or Path(__file__).parent / "reports" / "failures"
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


# ═══════════════════════════════════════════
# 3.5 语义校验 + 定点修正（E0 质量层）
# ═══════════════════════════════════════════

from stock_agent.validator import (
    validate_report,
    is_collapsed_report,
    StructuralCollapseError,
)


def _add_usage(a: dict, b: dict) -> dict:
    """两份 usage 成本字典逐项累加（保持 prompt/completion/total 可观测）"""
    return {k: a.get(k, 0) + b.get(k, 0) for k in ("prompt", "completion", "total")}


def _repair_report(report: dict, issues: list[str]) -> tuple[dict, dict]:
    """将违规清单回传 LLM，要求其输出修正后的完整 JSON，返回 (report, usage)

    修正 prompt 只要求修复违规处、禁止改动合规字段；解析失败时向上抛异常，
    由 analyze_with_validation 兜底保留原报告。
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    issues_text = "\n".join(f"- {issue}" for issue in issues)

    resp = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[
            {"role": "system", "content": (
                "你是 JSON 修正助手。用户会给你一份股票投研报告 JSON 和它违反的规则清单。"
                "请输出修正后的完整 JSON：只修复违反规则的部分，不要改动合规字段，"
                "不要输出任何解释文字或 markdown 包裹，只输出纯 JSON。"
            )},
            {"role": "user", "content": (
                f"违反的规则清单：\n{issues_text}\n\n"
                f"原始报告 JSON：\n{json.dumps(report, ensure_ascii=False)}"
            )},
        ],
        extra_body={"thinking": {"type": "enabled"}},
        reasoning_effort="high",
        max_tokens=16384,
    )

    content = resp.choices[0].message.content
    reasoning_content = getattr(resp.choices[0].message, 'reasoning_content', None)
    usage = {
        "prompt": resp.usage.prompt_tokens,
        "completion": resp.usage.completion_tokens,
        "total": resp.usage.total_tokens,
    }

    # 与主调用相同的剥离逻辑：```json 包裹 / content 为空时兜底 reasoning_content
    raw_text = content or ""
    if not raw_text.strip() and reasoning_content:
        raw_text = reasoning_content
    if "```json" in raw_text:
        raw_text = raw_text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in raw_text:
        raw_text = raw_text.split("```", 1)[1].split("```", 1)[0]
    raw_text = raw_text.strip()
    if not raw_text:
        raise RuntimeError("修正调用返回空内容")

    return _parse_json(raw_text), usage


def analyze_with_validation(markdown_report: str, stock_code: str = "") -> tuple[dict, dict]:
    """生成 + 语义校验 + 定点修正 —— 生产管线统一入口（替代裸 analyze 调用）

    流程：
      0. stock_code 非空 → 载入该股历史报告骨架作对比材料（E1，失败跳过不阻塞）
      1. analyze() 生成初始报告
      2. validate_report() 硬规则校验（见 stock_agent/validator.py）
      3. 有违规 → 违规清单回传 LLM 定点修正（最多 1 轮）
      4. 修正后仍有违规 → 报告附 _validation_issues 字段并打日志，不阻塞主流程
    usage 累积修正调用的 token，保证成本可观测。
    """
    # Step 0: 历史对比上下文（E1）——DB 不可用时优雅降级为无历史
    history_context = ""
    if stock_code:
        try:
            from database import get_recent_reports
            from stock_agent.history import build_history_context
            history_context = build_history_context(get_recent_reports(stock_code))
            if history_context:
                print(f"[analyze] 已注入 {stock_code} 历史对比上下文（{len(history_context)} 字符）", file=sys.stderr)
        except Exception as e:
            print(f"[analyze] ⚠️ 历史报告加载失败，按无历史继续: {e}", file=sys.stderr)

    try:
        report, usage = analyze(markdown_report, history_context)
    except StructuralCollapseError as e:
        # 截断坍塌是偶发的（取决于当次思考写多长）：整体重试生成一次，
        # 成本累积保持可观测；仍坍塌则抛错 → 前端明确提示失败，不存垃圾报告
        print(f"[analyze] ⚠️ {e}，自动整体重试生成一次", file=sys.stderr)
        report, usage2 = analyze(markdown_report, history_context)
        usage = _add_usage(e.usage, usage2)
    issues = validate_report(report)
    if not issues:
        return report, usage

    print(f"[analyze] ⚠️ 校验发现 {len(issues)} 处违规，尝试定点修正: {issues[:3]}", file=sys.stderr)
    try:
        repaired, repair_usage = _repair_report(report, issues)
        # 累积修正调用成本
        usage = _add_usage(usage, repair_usage)
        before = len(issues)
        # 结构门关先于完整校验：坍塌残片违规数反而少，防"谁少采纳谁"误纳，也省白校验
        if not is_collapsed_report(repaired):
            issues_after = validate_report(repaired)
            if len(issues_after) < before:
                report, issues = repaired, issues_after
                print(f"[analyze] → 修正后违规数 {before} → {len(issues)}", file=sys.stderr)
    except Exception as e:
        print(f"[analyze] ⚠️ 修正调用失败，保留原报告: {e}", file=sys.stderr)

    if issues:
        print(f"[analyze] ⚠️ 修正后仍剩 {len(issues)} 处违规（不阻塞）: {issues}", file=sys.stderr)
        report["_validation_issues"] = issues
    return report, usage


# ═══════════════════════════════════════════
# 4. 报告渲染（从 render 模块导入）
# ═══════════════════════════════════════════

from stock_agent.render import render_markdown  # noqa: F401 — 保持向后兼容，原调用方可继续 from analyze import render_markdown


# ═══════════════════════════════════════════
# 5. 飞书推送
# ═══════════════════════════════════════════

def push_to_feishu(md_report: str, stock_name: str, stock_code: str):
    """推送到飞书（复用现有 notifier）"""
    import requests

    if not FEISHU_WEBHOOK_URL:
        print("  ⚠️ 未配置 FEISHU_WEBHOOK_URL，跳过飞书推送")
        return False

    # 去掉 H1 标题行（飞书卡片已有 header，避免重复）
    lines = md_report.split("\n")
    start = 2 if len(lines) > 1 and lines[1] == "" else 1
    card_body = "\n".join(lines[start:])

    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"{stock_name}（{stock_code}）分析报告"},
                "template": "blue"
            },
            "elements": [
                {"tag": "markdown", "content": card_body},
                {"tag": "note", "elements": [
                    {"tag": "plain_text", "content": f"Karens Agent · 股票分析 · {datetime.now().strftime('%Y-%m-%d %H:%M')}"}
                ]}
            ]
        }
    }

    try:
        r = requests.post(FEISHU_WEBHOOK_URL, json=payload, timeout=10)
        if r.status_code == 200:
            print("  ✅ 飞书推送成功")
            return True
        else:
            print(f"  ❌ 飞书推送失败: {r.status_code} {r.text}")
            return False
    except Exception as e:
        print(f"  ❌ 飞书推送失败: {e}")
        return False


# ═══════════════════════════════════════════
# 6. 主入口
# ═══════════════════════════════════════════

async def main():
    import argparse
    from stock_agent.skill.report import generate_report_sync

    parser = argparse.ArgumentParser(description="A 股个股分析工具（实验 B）")
    parser.add_argument("stocks", nargs="?", default="600398",
                        help="股票代码，多个用逗号分隔，如 600519,000858")
    parser.add_argument("--push", action="store_true", help="推送到飞书")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    parser.add_argument("--watchlist", action="store_true", help="使用默认自选股列表")
    args = parser.parse_args()

    # 默认自选股
    DEFAULT_WATCHLIST = ["600398", "600519", "000858"]

    if args.watchlist:
        codes = DEFAULT_WATCHLIST
    else:
        codes = [c.strip() for c in args.stocks.split(",") if c.strip()]

    for code in codes:
        print(f"\n{'='*60}")
        print(f"  🔍 分析 {code}")
        print(f"{'='*60}")

        # 采集（SKILL 10 维度）
        print("📡 SKILL 采集数据...")
        try:
            data_md = generate_report_sync(code)
        except Exception as e:
            print(f"  ❌ 数据采集失败: {e}")
            continue

        # 分析
        print("🤖 LLM 分析...")
        try:
            report, usage = analyze_with_validation(data_md["markdown"], code)
        except DataIncompleteError as e:
            print(f"  ❌ 数据不完整，拒绝调用LLM: {e}")
            continue
        except Exception as e:
            print(f"  ❌ 分析失败: {e}")
            continue

        print(f"  ✅ Token: {usage['total']} | 评分: {report.get('score')} | {report.get('decision')}")

        stock_name = data_md.get("stock_name", code)
        md = render_markdown(code, report, usage, stock_name)

        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(f"\n{md}")

        # 保存
        out_dir = Path(__file__).parent / "reports"
        out_dir.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        out_file = out_dir / f"{code}_{ts}.md"
        out_file.write_text(md, encoding="utf-8")
        print(f"\n  💾 保存: {out_file}")

        # 飞书推送（第 2 参是 stock_name，489 行已从采集结果提取，勿再传 code）
        if args.push:
            push_to_feishu(md, stock_name, code)

    print(f"\n{'='*60}")
    print(f"  📋 实验 B 使用记录")
    print(f"  今天是第 ___ 天")
    print(f"  是否看了报告？___  是否影响了操作决策？___")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
