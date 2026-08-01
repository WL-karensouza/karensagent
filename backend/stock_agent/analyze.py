"""
实验 B：Dogfooding 最小可行分析脚本
用法：
    python backend/stock_agent/analyze.py 600398              # 终端查看报告
    python backend/stock_agent/analyze.py 600398 --push       # 查看 + 推送到飞书
    python backend/stock_agent/analyze.py 600398 --json       # JSON 格式输出
    python backend/stock_agent/analyze.py --watchlist         # 分析自选股列表
    python backend/stock_agent/analyze.py 600398,000858,300750  # 批量分析

连续使用 3 天后评估：
- 今天（Day 1）：____ 是否看了报告？____ 是否影响了操作决策？____
- Day 2：____ 是否主动使用？____ 是否影响了操作决策？____
- Day 3：____ 是否主动使用？____ 是否影响了操作决策？____
"""
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

def analyze(markdown_report: str) -> tuple[dict, dict]:
    """调用 DeepSeek Reasoner 分析 SKILL 数据报告，返回 (report, usage)。

    Args:
        markdown_report: SKILL 生成的 Markdown 格式综合数据报告
    """
    # 数据守卫：报告不能为空
    if not markdown_report or not markdown_report.strip():
        raise DataIncompleteError("数据报告为空，拒绝调用 LLM 以防止幻觉")

    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise RuntimeError("未设置 DEEPSEEK_API_KEY，请检查 .env 文件")

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    user_prompt = build_user_prompt(markdown_report)

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
        raise RuntimeError(
            f"DeepSeek Reasoner 返回空内容 "
            f"(content_len={len(content) if content else 0}, "
            f"reasoning_len={len(reasoning_content) if reasoning_content else 0}, "
            f"finish_reason={resp.choices[0].finish_reason})"
        )

    report = _parse_json(raw_text)
    return report, usage


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


def _parse_json(raw_text: str, max_retries: int = 2) -> dict:
    """容错 JSON 解析 — DeepSeek Reasoner 偶尔输出非法 JSON

    常见问题及修复策略：
      1. 末尾截断（finish_reason=length）→ 补全缺失的 }]
      2. 尾随逗号（"key": "val",}）→ 移除
      3. JSON 内嵌 markdown 代码块 → 二次剥离
    """
    import re as _re

    text = raw_text

    for attempt in range(max_retries + 1):
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            if attempt >= max_retries:
                raise  # 重试耗尽，抛出原始错误

            print(f"[analyze] ⚠️ JSON 解析失败 (尝试 {attempt+1}/{max_retries+1}): {e}", file=sys.stderr)

            # 策略 1：尾随逗号 — 删除 , 后紧跟 } 或 ] 的模式
            err_msg = str(e)
            if "trailing comma" in err_msg.lower() or "Expecting ',' delimiter" in err_msg or "Expecting value" in err_msg:
                fixed = _re.sub(r',(\s*[}\]])', r'\1', text)
                if fixed != text:
                    text = fixed
                    print(f"[analyze] → 已移除尾随逗号", file=sys.stderr)
                    continue

            # 策略 2：截断 — 尝试补全未闭合的括号
            open_braces = text.count('{') - text.count('}')
            open_brackets = text.count('[') - text.count(']')
            if open_braces > 0 or open_brackets > 0:
                text = text.rstrip()
                if text.endswith(','):
                    text = text[:-1]  # 移除末尾逗号再补
                text += ']' * open_brackets + '}' * open_braces
                print(f"[analyze] → 已补全 {open_braces}个}} {open_brackets}个]", file=sys.stderr)
                continue

            # 策略 3：JSON 前后可能有文字，按括号深度匹配提取最外层完整 {...}
            extracted = _extract_outermost_json(text)
            if extracted and extracted != text:
                text = extracted
                print(f"[analyze] → 已提取最外层 JSON", file=sys.stderr)
                continue

            raise  # 以上策略都不匹配，抛原始错误


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
            report, usage = analyze(data_md["markdown"])
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
