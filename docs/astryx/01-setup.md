# 01 · 安装与接入

## 硬性要求

| 项 | 要求 |
|---|---|
| React | **19 或更高**（`react` / `react-dom` 是 `@astryxdesign/core` 的 peer dependencies） |
| 包 | `@astryxdesign/core` + 一个主题包，如 `@astryxdesign/theme-neutral` |
| 构建 | Vite / Next.js 都行；**除非要深度定制样式，不需要任何构建插件** |

---

## 两种集成模式

| | A · 纯用（推荐起步） | B · StyleX 深度定制 |
|---|---|---|
| 做什么 | 只用组件 + 主题，业务样式自己写 CSS | 需要用 `xstyle` prop 或 `stylex.create()` |
| 额外依赖 | 无 | `@stylexjs/stylex`、`@stylexjs/unplugin`、`@astryxdesign/build` |
| 配置 | 无 | `vite.config` 加 `astryxStylex()` |

**先走 A**。A 模式下**不要用 `xstyle` prop**（它只吃 `stylex.create()` 的结果，传 `style={{}}` 会报错）。

---

## 接入步骤

### 1. 装包

```bash
npm install @astryxdesign/core @astryxdesign/theme-neutral
```

### 2. 初始化

```bash
npx @astryxdesign/cli init --all
```

`init` **非交互**，适合 AI agent / CI / 脚本。
不加 `--all` 只生成 AI 文档（`AGENTS.md`、`GEMINI.md`）；加了才额外给主题模板 `theme.template.ts` 和页面构建工作流。

### 3. 加主题

```bash
npx @astryxdesign/cli theme add neutral
```

会生成 `astryx-themes.ts`，导出 `themes` 和 `defaultThemeSlug`。

### 4. 入口挂主题

```tsx
import { Theme } from '@astryxdesign/core/theme'
import { themes, defaultThemeSlug } from './astryx-themes'

createRoot(el).render(
  <Theme theme={themes[defaultThemeSlug]}>
    <App />
  </Theme>
)
```

### 5. 入口导入基础样式（顺序不能反）

```ts
import '@astryxdesign/core/reset.css'
import '@astryxdesign/core/astryx.css'
```

---

## 目录结构（Vite 实测可用）

```
web/
├── index.html          # 入口 HTML
├── package.json
├── vite.config.ts
├── astryx-themes.ts    # theme add 生成，别手改
├── theme.template.ts   # init 生成，自定义主题时才用
├── AGENTS.md           # init 生成，AI 开发规矩
├── app/                # 页面
├── components/         # 业务组件
├── ui/                 # 类型、主题常量
├── stores/             # 状态
├── api/                # 数据请求
└── styles/globals.css  # 只放 Astryx 覆盖不到的全局样式
```

`index.html` 的入口脚本改到自己的入口文件：

```html
<script type="module" src="/app/main.tsx"></script>
```

`tsconfig.app.json` 的 `include` 要包含所有源码目录（默认只有 `src`）：

```json
"include": ["app", "components", "ui", "stores", "api", "styles"]
```

---

## package.json 建议脚本

```json
"scripts": {
  "dev": "vite",
  "build": "tsc -b && vite build",
  "astryx": "node node_modules/@astryxdesign/cli/clients/cli/bin/astryx.mjs"
}
```

避免每次敲长路径；也保证用的是**项目内锁定的版本**。
