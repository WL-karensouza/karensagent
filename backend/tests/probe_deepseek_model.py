#!/usr/bin/env python3
"""验证 DeepSeek V4-Flash-0731 模型是否已生效

2026-07-31 官方更新日志：DeepSeek-V4-Flash 正式版 API 公测上线
（版本号 DeepSeek-V4-Flash-0731，仅重后训练，架构与 Preview 一致），
API 调用方式不变，模型名仍为 deepseek-v4-flash。

本脚本从三个维度实测：
1. GET /models              — 服务端当前模型清单
2. chat/completions         — OpenAI 兼容接口实际调用，看响应 model 字段
3. /anthropic/v1/messages   — Anthropic 兼容接口实际调用（Claude Code 同通道）

用法：
    DEEPSEEK_API_KEY=sk-xxx python tests/probe_deepseek_model.py
"""
import json
import os
import sys

import requests

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
if not API_KEY:
    raise SystemExit("请先设置环境变量 DEEPSEEK_API_KEY")

BASE_OPENAI = "https://api.deepseek.com"
BASE_ANTHROPIC = "https://api.deepseek.com/anthropic"
MODEL = "deepseek-v4-flash"

HEADERS_OPENAI = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}
HEADERS_ANTHROPIC = {
    # DeepSeek 官方：Anthropic 兼容端点沿用同一 API Key
    "x-api-key": API_KEY,
    "Authorization": f"Bearer {API_KEY}",
    "anthropic-version": "2023-06-01",
    "Content-Type": "application/json",
}


def check_models() -> None:
    """方式 1：模型清单"""
    resp = requests.get(f"{BASE_OPENAI}/models", headers=HEADERS_OPENAI, timeout=30)
    resp.raise_for_status()
    ids = [m.get("id") for m in resp.json().get("data", [])]
    print("=" * 60)
    print(f"[1/3] GET {BASE_OPENAI}/models")
    print(f"  共 {len(ids)} 个模型:")
    for mid in ids:
        marker = "  <-- 本 session 使用" if mid and "flash" in mid else ""
        print(f"    - {mid}{marker}")


def check_chat() -> None:
    """方式 2：OpenAI 兼容实际调用"""
    resp = requests.post(
        f"{BASE_OPENAI}/chat/completions",
        headers=HEADERS_OPENAI,
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": "只回复两个字：ok"}],
            "max_tokens": 10,
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    print("=" * 60)
    print(f"[2/3] POST {BASE_OPENAI}/chat/completions (model={MODEL})")
    print(f"  响应 model 字段: {data.get('model')}")
    content = data["choices"][0]["message"].get("content")
    print(f"  回复内容: {content}")
    usage = data.get("usage", {})
    print(f"  用量: {usage}")


def check_anthropic() -> None:
    """方式 3：Anthropic 兼容实际调用（与 Claude Code 同通道）"""
    resp = requests.post(
        f"{BASE_ANTHROPIC}/v1/messages",
        headers=HEADERS_ANTHROPIC,
        json={
            "model": MODEL,
            "max_tokens": 10,
            "messages": [{"role": "user", "content": "只回复两个字：ok"}],
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    print("=" * 60)
    print(f"[3/3] POST {BASE_ANTHROPIC}/v1/messages (model={MODEL})")
    print(f"  响应 model 字段: {data.get('model')}")
    content = "".join(b.get("text", "") for b in data.get("content", []))
    print(f"  回复内容: {content}")
    print(f"  用量: {data.get('usage')}")
    print("=" * 60)


if __name__ == "__main__":
    print(f"验证目标模型: {MODEL}（官方 2026-07-31 更新为 V4-Flash-0731）\n")
    check_models()
    check_chat()
    check_anthropic()
    print("\n完成。若三处 model 字段均为 v4-flash 系且正常返回，说明已生效。")
