# 股票代码 → 公司名称映射 — 交接文档

**日期**: 2026-07-20
**来源**: 3D 办公室首页计划（`.claude/plans/cheerful-cuddling-honey.md`）

---

## 背景

当前 iFinD MCP 的多个接口无法稳定返回股票代码对应的公司中文名（如 `600519` → "贵州茅台"）。现有方案靠正则从自然语言文本中提取，失败率高，已确认为 bug。

## 问题根因

1. iFinD 的 `get_stock_summary` 返回自由格式自然语言文本，正则匹配"公司全称：XXX"不可靠
2. 其他高频接口（`stock_highfreq_quotes`、`get_stock_financials` 等）根本不返回公司名
3. 港股走 `global_stock_profile`，返回格式是 Markdown 管道表格，字段名也不统一
4. 当前代码 `_extract_stock_name()` 在 `backend/stock_agent/skill/report.py:404-436`

## 解决方案

**用东方财富公开 HTTP 接口做兜底**，在 iFinD 正则提取失败时调用。

### 探测结果

| 股票代码 | 描述 | 东方财富名称 | 耗时 |
|---------|------|-------------|------|
| 588000 | 科创50ETF | 科创50ETF龙头 | ~400ms |
| 688221 | 科创板 | 前沿生物-U | ~365ms |
| 601127 | 沪市主板 | 赛力斯 | ~374ms |
| 2513.HK | 港股 | 智谱 | ~400ms |
| 0700.HK | 港股蓝筹 | 腾讯控股 | ~400ms |
| 9988.HK | 港股蓝筹 | 阿里巴巴-W | ~400ms |

### 东方财富 API 参数

- URL: `https://push2.eastmoney.com/api/qt/stock/get`
- 参数: `fltt=2, invt=2, fields=f57,f58, secid={市场}.{代码}`
- `f57` = 代码, `f58` = 简称

### secid 构造规则

| 市场 | secid 格式 | 示例 |
|------|-----------|------|
| 沪市 (60/68/5开头) | `1.{code}` | `1.600519` → 贵州茅台 |
| 深市 (00/30开头) | `0.{code}` | `0.000001` → 平安银行 |
| 港股 (.HK结尾) | `116.{zfill(5)}` | `116.00700` → 腾讯控股 |

### AKShare 为什么不选

- `stock_individual_info_em()` — 当前版本 1.18.64 有 bug，3只A股全部报错
- `stock_zh_a_spot_em()` — 每次拉全量 5000+ 只，耗时 80s+，不适合实时查
- `stock_info_a_code_name()` — 不含 ETF 品种

## 实现计划

### 改动范围

只改 **1 个文件**: `backend/stock_agent/skill/report.py`

### 实现方式

在 `_extract_stock_name()` 函数末尾（第 436 行 `return stock_code` 之前），加入东方财富兜底：

```python
def _get_name_eastmoney(stock_code: str) -> str | None:
    """东方财富 HTTP 直调查询公司名称，A股+港股通用"""
    import requests
    code = stock_code.strip()
    # 港股 secid
    if code.endswith(".HK"):
        pure = code.replace(".HK", "")
        secid = f"116.{pure.zfill(5)}"
    else:
        # A股：清掉后缀，按首字判断市场
        pure = code.replace(".SH", "").replace(".SZ", "")
        market = "1" if pure[0] in ("6", "5") else "0"
        secid = f"{market}.{pure}"
    
    try:
        r = requests.get(
            "https://push2.eastmoney.com/api/qt/stock/get",
            params={"fltt": "2", "invt": "2", "fields": "f57,f58", "secid": secid},
            timeout=5,
        )
        data = r.json()
        name = data.get("data", {}).get("f58", "")
        if name and len(name) >= 2:
            return name
    except Exception:
        pass
    return None
```

然后在 `_extract_stock_name()` 中，`return stock_code` 之前插入：

```python
    # 正则失败 → 东方财富兜底
    fallback = _get_name_eastmoney(stock_code)
    if fallback:
        return fallback

    return stock_code  # 现有行
```

### 探测脚本

已创建的探测脚本（保留供后续调试）：
- `backend/tests/probe_stock_name.py` — A股多源对比
- `backend/tests/probe_hk_name.py` — 港股 secid 格式探测

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/stock_agent/skill/report.py` | `_extract_stock_name()` (L404-436) — 唯一要改的文件 |
| `backend/stock_agent/skill/__init__.py` | iFinD SKILL 调用封装 |
| `backend/routers/stock_api.py` | API 路由，无需改动（名称透传） |
| `backend/tests/probe_stock_name.py` | A股探测脚本 |
| `backend/tests/probe_hk_name.py` | 港股探测脚本 |

## 注意事项

1. 这是纯兜底逻辑——只有 iFinD 正则提取失败时才调用东方财富
2. 东财接口免费无需注册，但不要高并发（每次分析只调1次，无需限速）
3. ETF（5开头）的 secid 也用 `1`（沪市市场代码），已探测验证通过
4. 科创板股票名称带 `-U` 后缀（如"前沿生物-U"），这是正常行为
5. 零依赖 — 项目已有 `requests` 库，无需安装新包

## suggested skills

- 无特殊技能要求，这是独立 bugfix，直接改 `report.py` 即可
