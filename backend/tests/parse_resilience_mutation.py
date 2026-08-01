"""_parse_json 容错突变回归 — 用真实报告量化救回率（零 LLM 成本）

方法：取 DB 真实报告 JSON，系统性地破坏它，喂给 _parse_json 测救回率。
三类突变对应三种真实故障形态（E2 实验与线上日志挖出的）：
  1. 截断突变：25%/50%/75%/90%/95% 位置切断（模拟 finish_reason=length）
  2. 裸换行突变：字符串内注入未转义 \\n（模拟 DeepSeek 偶发控制字符）
  3. 尾随逗号突变：末尾 } 前塞 ,（模拟模型手抖）

救回标准：_parse_json 不抛异常，且结果含 score 或 decision（救出的是有意义的内容，
不是空壳）。截断过早（关键字段还没输出）救不回属合理，不计为策略失败。

用法：python tests/parse_resilience_mutation.py
"""
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from database import SessionLocal
from models import StockReport
from stock_agent.analyze import _parse_json

SAMPLE_SIZE = 21  # DB 新格式报告存量


def load_real_jsons(limit: int = SAMPLE_SIZE) -> list[str]:
    """从 DB 取真实报告 JSON 字符串（跳过解析不了的旧格式）"""
    db = SessionLocal()
    try:
        rows = db.query(StockReport).order_by(StockReport.id.desc()).limit(60).all()
    finally:
        db.close()
    out = []
    for r in rows:
        try:
            json.loads(r.report_json)
            out.append(r.report_json)
        except Exception:
            continue  # 旧 schema 遗留，非本回归目标
        if len(out) >= limit:
            break
    return out


def is_recovered(result) -> bool:
    """救回 = 解析成功 + 救出有意义的顶层字段"""
    return isinstance(result, dict) and ("score" in result or "decision" in result)


def mutation_truncation(jsons: list[str]) -> None:
    """截断突变：各位置切断，测括号补全 + 字符串闭合的救回率"""
    print("=== 突变 1：输出截断（finish_reason=length 形态）===")
    for pos in (0.25, 0.50, 0.75, 0.90, 0.95):
        rescued = 0
        for js in jsons:
            cut = js[: int(len(js) * pos)]
            try:
                if is_recovered(_parse_json(cut)):
                    rescued += 1
            except Exception:
                pass
        print(f"  截断在 {pos:>4.0%} 处：救回 {rescued}/{len(jsons)}")


def mutation_raw_newline(jsons: list[str]) -> None:
    """裸换行突变：rating_sentence 字符串内注入未转义换行（strict=False 应 100% 免疫）"""
    print("=== 突变 2：字符串内裸换行（控制字符形态）===")
    rescued = 0
    for js in jsons:
        idx = js.find("rating_sentence")
        if idx == -1:
            continue
        quote = js.find('"', js.find(":", idx) + 1)  # 值字符串的开引号
        corrupted = js[: quote + 1] + "第一行\n第二行" + js[quote + 1:]
        try:
            if is_recovered(_parse_json(corrupted)):
                rescued += 1
        except Exception:
            pass
    print(f"  裸换行：救回 {rescued}/{len(jsons)}（宽松模式预期 100%）")


def mutation_trailing_comma(jsons: list[str]) -> None:
    """尾随逗号突变：末尾 } 前塞 ,（尾随逗号策略应 100% 救回）"""
    print("=== 突变 3：尾随逗号 ===")
    rescued = 0
    for js in jsons:
        last = js.rfind("}")
        corrupted = js[:last] + ",}"
        try:
            if is_recovered(_parse_json(corrupted)):
                rescued += 1
        except Exception:
            pass
    print(f"  尾随逗号：救回 {rescued}/{len(jsons)}（预期 100%）")


def mutation_bare_quote(jsons: list[str]) -> None:
    """裸引号突变：字符串内注入未转义双引号（LLM 常见缺陷，如 所谓"陷阱"）"""
    print("=== 突变 4：字符串内未转义裸引号 ===")
    rescued = 0
    for js in jsons:
        idx = js.find("rating_sentence")
        if idx == -1:
            continue
        quote = js.find('"', js.find(":", idx) + 1)  # 值字符串开引号
        corrupted = js[: quote + 1] + '这里有"裸引号"注入' + js[quote + 1:]
        try:
            if is_recovered(_parse_json(corrupted)):
                rescued += 1
        except Exception:
            pass
    print(f"  裸引号：救回 {rescued}/{len(jsons)}")


def main():
    jsons = load_real_jsons()
    print(f"样本：DB 真实报告 {len(jsons)} 份\n")
    if not jsons:
        print("❌ 无可用样本")
        return
    mutation_truncation(jsons)
    mutation_raw_newline(jsons)
    mutation_trailing_comma(jsons)
    mutation_bare_quote(jsons)


if __name__ == "__main__":
    main()
