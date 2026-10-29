# 06 · 主题与设计 token

> 规矩：**禁止裸 hex、禁止裸 px、禁止 `:root` 覆盖**。颜色/间距/圆角全走 token，深色模式自动生效。
> 查看全部：`npx @astryxdesign/cli docs tokens`

---

## 主题：7 套

| slug | 名称 | 特点 | maintained |
|---|---|---|---|
| `neutral` | Neutral | 中性灰，"muted and minimal" | ✅ **唯一维护中** |
| `butter` | Butter | 暖奶油黄 + 蓝色强调，偏消费者 | ❌ |
| `chocolate` | Chocolate | 暖棕 + Fraunces 标题 | ❌ |
| `gothic` | Gothic | 深蓝灰 + 衬线，戏剧化 | ❌ |
| `matcha` | Matcha | 抹茶绿 | ❌ |
| `stone` | Stone | 石色 | ❌ |
| `y2k` | Y2K | 复古未来 | ❌ |

**实测细节**：
- 7 套的 `default` **全是 `no`** —— 没有内置默认主题，必须 `theme add <slug>` 显式挑一个
- 只有 `neutral` 是 `maintained: yes`，其余全是 `no`

```bash
npx @astryxdesign/cli theme list
npx @astryxdesign/cli theme add neutral
```

自定义主题：编辑 `theme.template.ts` 或用 `defineTheme()` 覆盖 token，**不要改 `astryx-themes.ts`（自动生成）**。

---

## 颜色 token（浅色 / 深色两套，`light-dark()` 自动切换）

### 语义色

| token | 浅色 | 深色 |
|---|---|---|
| `--color-accent` | `#0064E0` | `#2694FE` |
| `--color-background-body` | `#F1F4F7` | `#111112` |
| `--color-background-surface` | `#FFFFFF` | `#1F1F22` |
| `--color-background-card` | `#FFFFFF` | `#1F1F22` |
| `--color-background-muted` | 半透明蓝灰 | 半透明 |
| `--color-text-primary` | `#0A1317` | `#DFE2E5` |
| `--color-text-secondary` | `#4E606F` | `#AAAFB5` |
| `--color-text-disabled` | `#A4B0BC` | `#6F747C` |
| `--color-border` | 半透明 | 半透明 |
| `--color-border-emphasized` | `#CCD3DB` | `#494D53` |
| `--color-success` / `-muted` | `#0D8626` | 同 |
| `--color-error` / `-muted` | `#E3193B` | `#F5394F` |
| `--color-warning` / `-muted` | `#E9AF08` | `#F2C00B` |
| `--color-skeleton` | `#CCD3DB` | `#5A5E66` |

### 彩色族（每组 4 个：background / border / icon / text）

`blue` · `cyan` · `gray` · `green` · `orange` · `pink` · `purple` · `red` · `teal` · `yellow`

```css
--color-background-blue   /* 浅蓝底，适合卡片 */
--color-border-blue
--color-text-blue         /* 深蓝字，浅底上对比度足够 */
```

**用法示例**（不用自己配深浅）：

```tsx
const surface: CSSProperties = {
  background: 'var(--color-background-blue)',
  borderColor: 'var(--color-border-blue)',
  borderWidth: '1px',
  borderStyle: 'solid',
  borderRadius: 'var(--radius-container)',
  padding: 'var(--spacing-4)'
}
```

---

## 间距 token（4dp 基准）

| token | rem | token | rem |
|---|---|---|---|
| `--spacing-0` | 0 | `--spacing-5` | 1.25 |
| `--spacing-0-5` | 0.125 | `--spacing-6` | 1.5 |
| `--spacing-1` | 0.25 | `--spacing-7` | 1.75 |
| `--spacing-1-5` | 0.375 | `--spacing-8` | 2 |
| `--spacing-2` | 0.5 | `--spacing-9` | 2.25 |
| `--spacing-3` | 0.75 | … | … |
| `--spacing-4` | 1 | | |

组件的 `gap` / `padding` props 传数字时映射到这套 token。

---

## 圆角 token

| token | 值 | 用途 |
|---|---|---|
| `--radius-none` | 0 | |
| `--radius-inner` | 4px | 内部小元素 |
| `--radius-element` | 8px | 按钮、输入框 |
| `--radius-container` | 12px | 卡片、容器 |
| `--radius-page` | 28px | 大面板 |
| `--radius-chat` | 28px | 聊天气泡 |
| `--radius-full` | 9999px | 药丸 |

---

## 其他 token 组

| 组 | 说明 |
|---|---|
| `--font-family-*` | body / code / heading 字体栈 |
| `--font-size-base` = 14px，几何级数 `round(14 × 1.2^step)` | 字号 |
| `--duration-fast/medium/slow` + min/max | 动效时长 |
| `--ease-*` | 缓动曲线 |
| `--shadow-low/med/high` | 阴影 |
| `--size-*` | 控件高度 |

---

## cascade layer：最容易踩的坑

Astryx 用 CSS 层组织样式：`reset` 在 `@layer reset`，组件样式在 `@layer astryx-base`。

- 项目若引入 Tailwind 或已有全局 CSS / 旧 reset，**必须显式声明层顺序**，把每个样式表分配到明确的层
- **未分层的样式、以及排在后面层的样式，会盖掉组件样式——跟选择器特异性无关**

动样式前先跑：

```bash
npx @astryxdesign/cli docs migration/migration-setup
```
