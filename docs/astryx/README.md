# Astryx 设计与组件参考包

> **来源**：2026-10-29 在 CalmSwell 项目中实测 Astryx `0.7.4` 整理而成。
> **用途**：给 karensAgent 重做前端时当作业手册——所有结论都跑过命令验证，不是看文档抄的。
> **官网**：https://astryx.atmeta.com/docs/getting-started

---

## 5 分钟上手

```bash
# 1. 装依赖（React 必须 19+）
npm install @astryxdesign/core @astryxdesign/theme-neutral

# 2. 生成 AI 编码文档 + 主题与页面构建工作流
npx @astryxdesign/cli init --all

# 3. 挑一个主题
npx @astryxdesign/cli theme add neutral
```

**入口文件必须最先导入这两行**，否则组件渲染成无样式裸元素：

```ts
import '@astryxdesign/core/reset.css'
import '@astryxdesign/core/astryx.css'
```

**生成页面**（一条命令一个页面）：

```bash
npx @astryxdesign/cli template ai-chat ./app/ai-chat
```

---

## 目录

| 文件 | 内容 |
|---|---|
| [01-setup.md](01-setup.md) | 安装、接入、目录结构、用哪种集成模式 |
| [02-cli.md](02-cli.md) | CLI 命令全表 + 模板使用的四步流程 |
| [03-templates.md](03-templates.md) | **57 个页面模板全清单** + 命名陷阱 |
| [04-components.md](04-components.md) | **173 个组件清单** + 74 个导入路径陷阱 |
| [05-chat.md](05-chat.md) | 14 个 Chat 组件速查（做对话界面必看） |
| [06-tokens-themes.md](06-tokens-themes.md) | 7 套主题 + 颜色/间距/圆角 token |
| [07-pitfalls.md](07-pitfalls.md) | **实操踩过的坑**，做前端前先读这一页 |

`raw/` 下是 CLI 原始输出，供 grep 查细节：

- `raw/astryx-templates.txt` — `template --list` 全量（2880 行）
- `raw/astryx-components.txt` — `component` 全量（525 行）
- `raw/chat/*.md` — 14 个 Chat 组件的完整文档
- `raw/astryx-AGENTS.md` — Astryx 自动生成的开发规矩
- `raw/astryx-chat-components.md` — 之前整理的中文速查表（含组合骨架）

---

## 三条最省时间的结论

1. **别从零写 UI**。57 个页面模板覆盖了登录、表格、设置、看板、聊天、编辑器，几乎每个场景都有现成的。
2. **别按组件名拼 import 路径**。173 个组件里 74 个的模块路径和名字不一样，一律跑 `component <Name>` 看 `Import:` 行。
3. **别写裸 hex 和 px**。颜色/间距/圆角全走 token，深色模式自动生效。
