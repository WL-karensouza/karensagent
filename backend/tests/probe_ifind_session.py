"""
实验 10：MCP Session 空闲超时验证 (H7.2)

测试 MCP session 在空闲 N 分钟后是否自动断开。
方法:
  1. 先调一次确保 session 活跃
  2. 等待配置的时间
  3. 再次调用（不复用旧 session 的 _init 逻辑 — 脚本会强制重建）

默认测试间隔: 2分钟 和 5分钟（可通过命令行参数覆盖）

用法:
  python probe_ifind_session.py           # 默认: 2min + 5min
  python probe_ifind_session.py --wait 3  # 只测 3 分钟
  python probe_ifind_session.py --steps 1,5,10  # 测 1/5/10 分钟
"""
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

env_path = BACKEND_DIR / ".env"
if env_path.exists():
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, value = line.partition("=")
            if key and value:
                os.environ.setdefault(key.strip(), value.strip().strip("\"'"))

from ifind_call import call, _sessions, _init

STOCK = "688981.SH"
TOOL = "get_stock_info"
PARAMS = {"query": f"{STOCK} 收盘价"}

OUTPUT_DIR = Path(__file__).parent / "probe_results"
OUTPUT_DIR.mkdir(exist_ok=True)


def test_session_call(step_label, server="stock"):
    """执行一次 MCP 调用，返回结果 + 耗时"""
    start = datetime.now()
    try:
        result = call(server, TOOL, PARAMS)
        elapsed = (datetime.now() - start).total_seconds()
        return {
            "ok": result.get("ok", False),
            "elapsed_s": round(elapsed, 2),
            "error": result.get("error") if not result.get("ok") else None,
            "session_active": server in _sessions,
        }
    except Exception as e:
        elapsed = (datetime.now() - start).total_seconds()
        return {
            "ok": False,
            "elapsed_s": round(elapsed, 2),
            "error": str(e),
            "session_active": server in _sessions,
        }


def force_new_session(server="stock"):
    """强制清除旧 session，模拟长时间空闲后重新连接"""
    if server in _sessions:
        del _sessions[server]
        print(f"  🔄 已清除 {server} session（模拟空闲断开）")


def main():
    # 解析命令行
    import argparse
    parser = argparse.ArgumentParser(description="MCP Session 超时测试")
    parser.add_argument("--steps", type=str, default="2,5",
                        help="逗号分隔的等待分钟数，如 '1,5,10'")
    parser.add_argument("--skip-wait", action="store_true",
                        help="跳过等待，直接测试 session 重用 vs 重建的性能差")
    args = parser.parse_args()

    wait_minutes = [int(m) for m in args.steps.split(",")]

    print("=" * 60)
    print("实验 10：MCP Session 空闲超时验证")
    print(f"时间: {datetime.now().isoformat()}")
    print(f"等待间隔: {wait_minutes} 分钟")
    print(f"目标: {STOCK} / {TOOL}")
    print("=" * 60)

    results = []

    # ── 基线: 首次调用（冷启动） ──
    print("\n📡 基线测试 (冷启动，建立新 session)...")
    # 清除所有旧 session
    for s in list(_sessions.keys()):
        del _sessions[s]

    r0 = test_session_call("baseline")
    status = "✅" if r0["ok"] else "❌"
    print(f"  {status} {'成功' if r0['ok'] else '失败: ' + str(r0.get('error',''))} | 耗时: {r0['elapsed_s']}s | session: {r0['session_active']}")
    results.append({"step": "baseline_cold", **r0})

    # ── 立即第二次（热调用，session 复用） ──
    print("\n🔥 热调用测试 (session 复用)...")
    r1 = test_session_call("hot_reuse")
    status = "✅" if r1["ok"] else "❌"
    print(f"  {status} {'成功' if r1['ok'] else '失败: ' + str(r1.get('error',''))} | 耗时: {r1['elapsed_s']}s | session: {r1['session_active']}")
    results.append({"step": "hot_reuse", **r1})

    # ── 跳过等待模式 ──
    if args.skip_wait:
        print("\n⚠️ --skip-wait 模式，跳过空闲等待测试")
    else:
        # ── 按配置的间隔测试 ──
        for wait_min in wait_minutes:
            wait_sec = wait_min * 60

            print(f"\n⏳ 等待 {wait_min} 分钟 ({wait_sec}秒)...")
            print(f"   开始等待: {datetime.now().strftime('%H:%M:%S')}")

            # 分段 sleep，每 60s 打印一次进度
            for elapsed_sec in range(0, wait_sec, 60):
                remaining = wait_sec - elapsed_sec
                chunk = min(60, remaining)
                time.sleep(chunk)
                if remaining > 60:
                    print(f"   剩余: {remaining // 60} 分钟...")

            print(f"   等待结束: {datetime.now().strftime('%H:%M:%S')}")

            # ── 测试 A: 复用旧 session ──
            print(f"  [A] 复用旧 session...")
            r_a = test_session_call(f"idle_{wait_min}m_reuse")
            status_a = "✅" if r_a["ok"] else "❌"
            print(f"  {status_a} {'成功' if r_a['ok'] else '失败: ' + str(r_a.get('error',''))} | 耗时: {r_a['elapsed_s']}s | session: {r_a['session_active']}")

            # ── 测试 B: 强制重建 session ──
            force_new_session("stock")
            print(f"  [B] 重建 session...")
            r_b = test_session_call(f"idle_{wait_min}m_rebuild")
            status_b = "✅" if r_b["ok"] else "❌"
            print(f"  {status_b} {'成功' if r_b['ok'] else '失败: ' + str(r_b.get('error',''))} | 耗时: {r_b['elapsed_s']}s | session: {r_b['session_active']}")

            results.append({
                "step": f"idle_{wait_min}m_reuse",
                "wait_min": wait_min,
                **r_a,
            })
            results.append({
                "step": f"idle_{wait_min}m_rebuild",
                "wait_min": wait_min,
                **r_b,
            })

    # ── 汇总 ──
    print("\n" + "=" * 60)
    print("📋 汇总")
    print("=" * 60)

    for r in results:
        step = r["step"]
        ws = r.get("wait_min", "-")
        elapsed = r["elapsed_s"]
        ok = "✅" if r["ok"] else "❌"
        print(f"  {ok} {step:25s} | 等待={ws}分 | 耗时={elapsed}s | session={r['session_active']}")

    # 性能对比
    cold = next((r for r in results if r["step"] == "baseline_cold"), None)
    hot = next((r for r in results if r["step"] == "hot_reuse"), None)

    if cold and hot:
        speedup = cold["elapsed_s"] / hot["elapsed_s"] if hot["elapsed_s"] > 0 else 0
        print(f"\n  冷启动耗时: {cold['elapsed_s']}s")
        print(f"  热复用耗时: {hot['elapsed_s']}s")
        print(f"  加速比: {speedup:.0f}x")

    # ── 保存 ──
    output_path = OUTPUT_DIR / f"session_probe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n💾 结果已保存: {output_path}")

    # ── 判定 ──
    all_ok = all(r["ok"] for r in results)
    if all_ok:
        print(f"\n✅ 实验 10 通过！所有 session 场景调用成功")
        return 0
    else:
        failed = [r for r in results if not r["ok"]]
        for f in failed:
            print(f"  ❌ {f['step']}: {f.get('error', 'unknown')}")
        print(f"\n⚠️ 实验 10 部分失败：{len(failed)} 次调用失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
