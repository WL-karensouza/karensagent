"""SKILL 报告编排器 — 门面

collect.py 负责采集、parse.py 负责解析、format.py 负责格式化；
本文件只保留 generate_report_sync / generate_report_stream 两个主入口。
"""
import asyncio
import time
from datetime import datetime

# 以下 re-export 保持向后兼容（测试与调用方仍从 stock_agent.skill.report 取值）
from ..datasources.eastmoney import (  # noqa: F401
    _get_name_eastmoney, _get_name_tencent, _fetch_ohlcv_eastmoney,
)
from . import call_skill, extract_text, extract_raw  # noqa: F401
from .collect import (  # noqa: F401
    DIMENSIONS, HK_DIMENSIONS, RATE_LIMIT_INTERVAL,
    _dimensions_for, _news_time_params, _resolve_summary_query,
    _strip_error_prefix, _call_dim_with_retry, _build_params,
)
from .format import (  # noqa: F401
    _format_sse, _enrich_performance, _market_suffix, normalize_stock_code,
    _format_indicators_markdown,
)
from .parse import (  # noqa: F401
    _clean_header, _parse_tsv_sections, _table_rows_to_prose,
    _format_news_prose, _raw_to_prose, _name_from_pipe_table,
    _extract_stock_name, _parse_ohlcv_table,
)


# ═══════════════════════════════════════════
# 异步版：SSE 流式生成器（FastAPI StreamingResponse 用）
# ═══════════════════════════════════════════

async def generate_report_stream(stock_code: str, dimensions: list[str] | None = None):
    """异步生成综合数据报告，yield SSE 事件

    Args:
        stock_code: 股票代码
        dimensions: 可选，指定要采集的维度 key 列表；传 None 则采集全部 10 个维度

    complete 事件包含：
      - report: 完整 Markdown（保留供投研报告使用）
      - sections: {dim_key: prose_text, ...}  各维度客观陈述文章
    """
    report_parts = []
    raws = {}          # dim_key → extract_raw() 结果
    has_critical_failure = False
    loop = asyncio.get_running_loop()

    # 归一化代码并按市场选择维度表（港股走 global_stock）
    stock_code = normalize_stock_code(stock_code)
    all_dims = _dimensions_for(stock_code)

    # 如果指定了维度，只处理选中的维度
    active_dims = [d for d in all_dims if dimensions is None or d["key"] in dimensions]
    total = len(active_dims)

    yield _format_sse("start", {"stock_code": stock_code, "total": total})

    for i, dim in enumerate(active_dims):
        yield _format_sse("progress", {
            "stage": dim["key"],
            "label": dim["label"],
            "status": "running",
            "current": i + 1,
            "total": total,
        })

        try:
            text, raw = await loop.run_in_executor(
                None, _call_dim_with_retry, dim, stock_code,
            )

            # performance 维度：基于 OHLCV 自行计算全部技术指标
            # _enrich_performance 内含东财同步 HTTP，必须丢线程池避免阻塞事件循环
            if dim["key"] == "performance":
                text = await loop.run_in_executor(
                    None, _enrich_performance, text, stock_code
                )

            report_parts.append(f"## {dim['label']}\n\n{text}")
            raws[dim["key"]] = raw

            yield _format_sse("progress", {
                "stage": dim["key"],
                "label": dim["label"],
                "status": "done",
                "current": i + 1,
                "total": total,
            })

        except Exception as e:
            error_msg = str(e)
            if dim["critical"]:
                has_critical_failure = True

            report_parts.append(
                f"## {dim['label']}\n\n> ⚠️ 数据获取失败：{error_msg}"
            )
            raws[dim["key"]] = None

            yield _format_sse("progress", {
                "stage": dim["key"],
                "label": dim["label"],
                "status": "error",
                "error": error_msg,
                "current": i + 1,
                "total": total,
            })

        # 维度间限速（最后一项不延迟）
        if i < total - 1:
            await asyncio.sleep(RATE_LIMIT_INTERVAL)

    # 组装完整 Markdown 报告（保留，供投研报告使用）
    # _extract_stock_name 兜底走东财同步 HTTP，同样丢线程池
    stock_name = await loop.run_in_executor(
        None, _extract_stock_name, raws.get("summary"), stock_code
    )
    header = f"# {stock_name}（{stock_code}）综合数据报告\n\n"
    header += f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    if has_critical_failure:
        header += "> ⚠️ **注意**：关键数据维度获取失败，报告可能不完整。\n\n"
    header += "---\n\n"
    full_markdown = header + "\n\n".join(report_parts)

    # 构建 sections：每维度独立客观陈述文章
    sections = {}
    for dim in active_dims:
        raw = raws.get(dim["key"])
        sections[dim["key"]] = _raw_to_prose(raw, dim["key"])

    yield _format_sse("complete", {
        "report": full_markdown,
        "sections": sections,
        "stock_code": stock_code,
        "stock_name": stock_name,
        "has_critical_failure": has_critical_failure,
    })


# ═══════════════════════════════════════════
# 同步版：后台线程直接调用（analyze / trigger 内部用）
# ═══════════════════════════════════════════

def generate_report_sync(stock_code: str, dimensions: list[str] | None = None) -> dict:
    """同步生成综合数据报告

    用于后台线程（_run_analysis / _run_watchlist_analyze）。

    Args:
        stock_code: 股票代码
        dimensions: 可选，指定要采集的维度 key 列表；传 None 则采集全部 10 个维度

    Returns:
        {"markdown": str, "stock_code": str, "stock_name": str,
         "sections": {dim_key: prose, ...}, "has_critical_failure": bool}

        stock_code 为归一化后的代码（如 HK2513 → 2513.HK）；
        has_critical_failure 为 True 表示关键维度（实时行情/基本信息）失败，
        上层应据此硬终止（勿拿失败数据调 LLM）。
    """
    parts = []
    raws = {}
    has_critical_failure = False

    # 归一化代码并按市场选择维度表（港股走 global_stock）
    stock_code = normalize_stock_code(stock_code)
    all_dims = _dimensions_for(stock_code)

    # 如果指定了维度，只处理选中的维度
    active_dims = [d for d in all_dims if dimensions is None or d["key"] in dimensions]

    for i, dim in enumerate(active_dims):
        try:
            text, raw = _call_dim_with_retry(dim, stock_code)

            # performance 维度：基于 OHLCV 自行计算全部技术指标
            if dim["key"] == "performance":
                text = _enrich_performance(text, stock_code)

            parts.append(f"## {dim['label']}\n\n{text}")
            raws[dim["key"]] = raw

        except Exception as e:
            if dim["critical"]:
                has_critical_failure = True
            parts.append(f"## {dim['label']}\n\n> ⚠️ 数据获取失败：{e}")
            raws[dim["key"]] = None

        # 限速
        if i < len(active_dims) - 1:
            time.sleep(RATE_LIMIT_INTERVAL)

    # 从 summary 维度中提取公司全称
    stock_name = _extract_stock_name(raws.get("summary"), stock_code)

    header = f"# {stock_name}（{stock_code}）综合数据报告\n\n"
    header += f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    if has_critical_failure:
        header += "> ⚠️ **注意**：关键数据维度获取失败，报告可能不完整。\n\n"
    header += "---\n\n"

    # 构建 sections
    sections = {}
    for dim in active_dims:
        raw = raws.get(dim["key"])
        sections[dim["key"]] = _raw_to_prose(raw, dim["key"])

    return {
        "markdown": header + "\n\n".join(parts),
        "stock_code": stock_code,
        "stock_name": stock_name,
        "sections": sections,
        "has_critical_failure": has_critical_failure,
    }
