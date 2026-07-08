# 同花顺 iFinD 数据接口接入 — 交接文档

> 创建时间：2026-07-08
> 状态：⏳ 等待用户申请免费账号，获取 token 后继续

---

## 一、当前项目状态

### 已有新闻采集源（fallback 链）

```
akshare (东方财富) → 搜狗微信搜索 → 百度新闻搜索
```

三个源均返回 `list[dict]`，格式统一为 `{"title": "新闻标题", "time": "发布时间"}`。

### 已知痛点

- 小盘股（如 688797）在上述三个源中经常返回空，导致报告消息面章节显示 **"无近期新闻数据"**
- 当前没有任何公告/研报数据源
- 当前没有概念板块数据，市场环境章节缺少"这只股属于什么概念"的上下文

---

## 二、同花顺 iFinD API 调研结论

### 平台概况

| 项目 | 详情 |
|------|------|
| 官方入口 | `http://quantapi.10jqka.com.cn` |
| 产品名 | iFinD QuantAPI |
| 免费版 | ✅ 有，注册 iFinD 账号即可使用，无需申请试用 |
| 支持语言 | Python、C++、Java、MATLAB、R、C#、HTTP |
| 下载中心 | `https://quantapi.10jqka.com.cn/gwstatic/static/ds_web/quantapi-web/download.html` |

### 接入方式（二选一）

| 方式 | 说明 | 推荐度 |
|------|------|:---:|
| **SDK** | 下载 Windows SDK → 超级命令客户端登录 → `pip install iFinDAPI` → `from iFinDPy import *` | ⭐⭐⭐ |
| **HTTP API** | 直接 HTTP 请求，无需 SDK，token 认证 | ⭐⭐ |

建议优先尝试 HTTP API 方式，轻量无依赖。

### Python SDK 安装命令

```bash
pip install iFinDAPI
```

登录示例：
```python
from iFinDPy import *
THS_iFinDLogin("账号", "密码")
```

---

## 三、接入优先级（分三批）

### 🥇 第一优先：新闻 + 公告

**目标**：在现有新闻 fallback 链最前面插入同花顺新闻源。

**改动范围**：

| 文件 | 改动 | 说明 |
|------|------|------|
| `backend/stock_agent/fetcher.py` | `+30` 行 | 新增 `_fetch_news_ths()` 函数，调用同花顺新闻/公告 API |
| `backend/stock_agent/fetcher.py` | `~5` 行 | 在 `fetch_stock_data()` 新闻采集链**最前面**插入同花顺 |
| `backend/stock_agent/skills/news.py` | 不动 | 下游无需改动 |

**新 fallback 链**：
```
同花顺 API（新增） → akshare (东方财富) → 搜狗微信 → 百度新闻
```

**免费额度**：公告查询 10000 次/月，对我们足够。

---

### 🥈 第二优先：概念板块

**目标**：新增概念板块数据，丰富市场环境章节。

**改动范围**：

| 文件 | 改动 | 说明 |
|------|------|------|
| `backend/stock_agent/fetcher.py` | `+20` 行 | 新增 `_fetch_concept_ths()` 函数 |
| `backend/stock_agent/skills/market_env.py` | `~15` 行 | 在 `market_env_skill` 中解析概念数据 |
| `backend/stock_agent/skills/__init__.py` | `~5` 行 | 更新 `market_env_skill.instructions`，加入概念分析指令 |
| `backend/stock_agent/analyze.py` | 不动 | 渲染层无需改动 |

**市场环境章节增强效果**：
> 该股属于"机器人概念""工业母机"板块，近期概念热度中等。在当前市场偏好科技成长的风格下…

---

### 🥉 第三优先：龙虎榜

**目标**：接入龙虎榜数据，让关注点章节能区分游资 vs 机构。

**改动范围**：

| 文件 | 改动 | 说明 |
|------|------|------|
| `backend/stock_agent/fetcher.py` | `+25` 行 | 新增 `_fetch_lhb_ths()` 函数 |
| `backend/stock_agent/skills/capital.py` | `~10` 行 | 资金面技能中注入龙虎榜数据 |
| `backend/stock_agent/skills/__init__.py` | `~5` 行 | 更新 `capital_skill.instructions` |

**关注点章节增强效果**：
> 龙虎榜显示今日买方以游资为主——游资主导则短线快进快出波动大…

---

## 四、待办事项

### 用户侧

- [ ] 访问 `http://quantapi.10jqka.com.cn`，注册 iFinD 免费账号
- [ ] 获取登录凭证（账号 + 密码 / token）
- [ ] （可选）下载 Windows SDK 备用

### 开发侧（用户拿到 token 后）

- [ ] 需求澄清：确认优先接入哪些维度的数据
- [ ] 先写一个最小 demo 验证 `iFinDPy` 或 HTTP API 可用
- [ ] 按 TDD 流程编写：RED → GREEN → REFACTOR
- [ ] 第一优先：`_fetch_news_ths()` 接入新闻 fallback 链
- [ ] 第二、第三优先按需推进

---

## 五、参考链接

| 资源 | 地址 |
|------|------|
| 同花顺 QuantAPI 官网 | `http://quantapi.10jqka.com.cn` |
| 下载中心 | `https://quantapi.10jqka.com.cn/gwstatic/static/ds_web/quantapi-web/download.html` |
| 部署说明 | `https://quantapi.51ifind.com/gwstatic/static/ds_web/quantapi-web/help-center/deploy.html` |
| 免费版权限说明 | `https://quantapi.51ifind.com/gwstatic/static/ds_web/quantapi-web/help-center/permission.html` |
| 网页版超级命令 | `https://quantapi.10jqka.com.cn/gwstatic/static/ds_web/super-command-web/index.html` |
| vnpy_ifind (社区封装) | `https://github.com/vnpy/vnpy_ifind` |
