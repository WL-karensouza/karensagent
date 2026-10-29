# 07 · 实操踩坑合集

> 这些都是 2026-10-29 在真实项目里**跑出来的**，不是看文档总结的。

---

## 一、官方规矩（来自 Astryx 自动生成的 AGENTS.md）

1. **不写 `<div>`**——布局用 `VStack` / `HStack` / `Stack` / `Grid` / `Layout`
2. **不写裸 hex 与 px**——一律走 token 或组件 props
3. **不写 `:root` 覆盖**——自定义颜色走 `defineTheme`
4. **页面从模板起步**，保留骨架（frame / gap / padding），只换内容
5. **`Badge` 只用于计数**，不要当标签用
6. **密集数据用行**（`Table` / `List`/`Item`），不要卡片列表套
7. A 模式（不上 StyleX）下**不要用 `xstyle` prop**——它只吃 `stylex.create()` 的结果

---

## 二、布局坑

### 1. ChatLayout 撑不满高度

**现象**：聊天界面只占内容高度，输入框悬在页面中间，下方大片空白。

**原因**：`ChatLayout` 靠 `flex: 1` 撑满父容器，而 Astryx 的 `<Theme>` 包装器是 `display: contents`，高度传不下去。

**解法**：外面套一层给定高度的 flex 容器。

```tsx
<VStack style={{ height: '100%', width: '100%', maxWidth: '55rem', marginInline: 'auto' }}>
  <ChatLayout composer={...}>{...}</ChatLayout>
</VStack>
```

同时确认 `html, body, #root { height: 100% }`。

---

### 2. VStack 把按钮拉成整行宽

**现象**：`VStack` 里的 `<Button>` 撑满整行、文字居中，看着像错位。

**原因**：`VStack` 默认交叉轴 `stretch`。

**解法**：用 `HStack` 包一层，按钮恢复自然宽度并左对齐。

```tsx
<HStack>
  <Button label="问题文本" variant="ghost" size="sm" onClick={...} />
</HStack>
```

---

### 3. Stack 的对齐值不是 CSS 值

| 你可能会写 | 正确写法 |
|---|---|
| `vAlign="baseline"` | `vAlign="center"`（**不支持 baseline**） |
| `hAlign="space-between"` | `hAlign="between"` |
| `hAlign="center"` | ✅ 可用 |

`vAlign` 可选：`center` / `end` / `start` / `stretch`
`hAlign` 可选：`around` / `between` / `center` / `end` / `evenly` / `start`

---

## 三、导入坑

### 4. 74 个组件的模块路径 ≠ 组件名

详见 [04-components.md](04-components.md)。一句话：**跑 `component <Name>` 照抄 `Import:` 行**。

### 5. `Theme` 是小写模块

```ts
import { Theme } from '@astryxdesign/core/theme'   // ✅
import { Theme } from '@astryxdesign/core/Theme'   // ❌
```

### 6. hooks 不在组件目录

```ts
import { useStreamingText } from '@astryxdesign/core/hooks'   // ✅
```

---

## 四、模板坑

### 7. 生成模板后可能提示缺依赖

`ai-chat-landing` 生成后提示 `npm install @heroicons/react@"^2.2.0"`。
**生成完立刻看终端最后几行**。不需要那些图标就改写掉，比装依赖干净。

### 8. 模板文件极大，别硬删

`ai-chat-landing/page.tsx` 有 478 行，包含分类切换、模式选择、@ 提及、语音、附件抽屉。
只想要「标题 + 输入框 + 卡片」时，**照骨架重写一个 90 行的组件**比删改 478 行更快。

---

## 五、样式坑

### 9. cascade layer 顺序

未分层的 CSS 会盖掉组件样式，且**与选择器特异性无关**。
项目里有 Tailwind 或旧 reset 时，必须显式声明层顺序。

```bash
npx @astryxdesign/cli docs migration/migration-setup
```

### 10. 深色模式是白拿的

彩色族 token 全部自带 `light-dark()`，用 token 就有深色模式；写死 hex 就丢了。

---

## 六、验证方法（很省事）

改完界面**不要只看代码**，用浏览器实测：

```bash
npm run dev
```

然后用 Chrome DevTools 检查两项：

```js
// 布局是否撑满
document.querySelector('.astryx-chat-layout').getBoundingClientRect().height

// 某个 token 是否真的生效
getComputedStyle(el).color
```

实测发现「颜色没生效」「高度没撑满」这类问题，靠看代码几乎找不到。
