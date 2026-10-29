# 08 · Vue 复刻指南（不用 React，只借设计）

> **背景**：karensAgent 前端是 Vue 3.5 + Vite，astryx 是 React 19 组件库。
> 本文记录「不引入 React、纯用 Vue 复刻 astryx 视觉」的可行方法与实操要点。
> **结论先行**：能做，且比预想轻——因为 astryx 的样式层本质就是 CSS 变量。
>
> 2026-10-29 实测验证（`D:\tmp\astryx-probe`），非文档推测。

---

## 一、前置结论

| 问题 | 答案 |
|---|---|
| 源码能看到吗 | **能**，`facebook/astryx`，MIT 许可，npm 包内含未压缩 `src/` |
| 功能实现能看懂吗 | **能**，逻辑简单，大头是样式和注释 |
| Vue 能复刻吗 | **能**，视觉可 100% 复刻；交互组件按需取舍 |

---

## 二、源码获取（三个入口）

### 1. 生成页面模板

```bash
npx @astryxdesign/cli@0.7.4 template ai-chat-landing ./out
```

产出 `out/page.tsx`（478 行），是可读的 React 页面编排代码。

### 2. 读组件源码（推荐）

装包后源码就在 `node_modules` 里，**未压缩**：

```bash
npm install @astryxdesign/core@0.7.4 --no-save
ls node_modules/@astryxdesign/core/src/Chat/
```

每个组件都带 `.tsx` 源码 + `.test.tsx` 测试，实现和边界行为一目了然。

### 3. GitHub 仓库

`https://github.com/facebook/astryx` —— MIT 许可，可自由抄改。

---

## 三、复刻难度分三档

### 第一档：样式与 token —— 100% 可复刻

astryx 用 StyleX 写样式，**翻译过来就是普通 CSS 变量**。实例（`ChatMessageBubble.tsx` 原样）：

```js
borderRadius: radiusVars['--radius-chat'],      // var(--radius-chat)
fontSize: typeScaleVars['--text-body-size'],    // var(--text-body-size)
paddingInline: spacingVars['--spacing-4'],      // var(--spacing-4)
backgroundColor: colorVars['--color-neutral'],  // var(--color-neutral)
maxWidth: 'max(80%, 280px)',                    // 原样照抄
```

**没有任何 React 特有魔法**，逐条抄成 CSS 即可。

### 第二档：展示类组件 —— 约 95%，工时低

如 `ChatMessage` / `ChatMessageBubble` / `ChatMessageList`。

源码 295–346 行，但**绝大部分是注释和样式定义**，真正的逻辑只有：
- 从 context 读 `sender`（`user` / `assistant`）
- 按 sender 切换背景色
- 组合 `name` / `metadata` 插槽

Vue 版本约 **80 行**即可覆盖。

### 第三档：交互类组件 —— 可复刻但成本高

| 组件 | 行数 | 为什么贵 |
|---|---|---|
| `ChatComposerInput.tsx` | 940 | @提及、token 插入、选区管理 |
| `useTriggerMenu.tsx` | 1013 | 触发菜单（`@` / `/`）的完整交互 |
| `ChatToolCalls.tsx` | 712 | 工具调用折叠面板 |

**这一段要按需取用**，没需求就别复刻。

---

## 四、token 映射表

astryx 与 karens 都用 CSS 变量，结构一致，逐项映射即可。

| astryx token | 实际值 | karens 对应 | 备注 |
|---|---|---|---|
| `--spacing-3` | `0.75rem` | 无 | 4px 步进体系 |
| `--spacing-4` | `1rem` | 无 | 同上 |
| `--radius-chat` | `28px` | `--radius-lg: 20px` | 气泡专用，比卡片更圆 |
| `--text-body-size` | `14px` | 无 | 正文字号 |
| `--color-neutral` | 见主题包 | `--bg-card: #FFFFFF` | 气泡底色 |
| — | — | `--accent: #D97706` | karens 品牌琥珀色 |

> **注意**：astryx 的彩色族 token 自带 `light-dark()`，用 token 就白拿深色模式；
> karens 现有 `src/style.css` 的 `:root` 是单套浅色，复刻时要么新增深色变量，
> 要么明确不做深色模式。

---

## 五、karens 实际复刻清单

以「问答助理面板」为目标，**只需要复刻以下四块**，约占模板的 20%：

| 要复刻 | astryx 来源 | 工作量 |
|---|---|---|
| 空态（问候语 + 输入框 + 推荐卡片） | `ai-chat-landing/page.tsx` 的问候区 + `ToggleButtonGroup` + `ClickableCard` | 中 |
| 消息列表 | `ChatMessageList` / `ChatMessage` | 低 |
| 消息气泡 | `ChatMessageBubble` | 低 |
| 输入框 | `ChatComposer` / `ChatComposerInput`（**去掉** @提及、附件、语音） | 中 |

**不需要复刻**（模板里有但用不上）：
`@` 提及系统、`/` 命令系统、附件抽屉、语音听写、模式切换菜单、分类筛选。

---

## 六、复刻操作步骤

1. **先取参考源码**
   ```bash
   npx @astryxdesign/cli@0.7.4 template ai-chat-landing ./ref
   ```
   `./ref/page.tsx` 就是页面编排的对照物。

2. **抽 token**：把用到的 `--spacing-*`、`--radius-chat`、`--color-*` 落到项目 CSS 变量表，
   **不要**在组件里写裸 hex / px。

3. **建 Vue 组件**：结构照搬，`ReactNode` 插槽 → Vue `<slot>`，
   `useState` → `ref`，`style={}` → `class` + CSS。

4. **图标替换**：模板依赖 `@heroicons/react`（React 版），
   Vue 项目需换成等价的 SVG 或 `@heroicons/vue`。**能不装依赖就手写 SVG**。

5. **浏览器实测**，别只读代码（见第九节）。

---

## 七、真值对照：气泡样式的完整参考

`ChatMessageBubble` 的核心样式（可直接翻译成 CSS）：

```css
.chat-bubble {
  display: flex;
  flex-direction: column;
  max-width: max(80%, 280px);
  border-radius: var(--radius-chat);   /* 28px，比卡片圆 */
  font-family: var(--font-family-body);
  font-size: var(--text-body-size);    /* 14px */
  line-height: var(--text-body-leading);
  overflow-wrap: break-word;
  word-break: break-word;
  /* 内边距按 density 分三档 */
  padding-block: var(--spacing-3);     /* 0.75rem */
  padding-inline: var(--spacing-4);    /* 1rem */
}
.chat-bubble--ghost {
  background-color: transparent;       /* 透明底但保留内边距，用于对齐非气泡内容 */
}
```

> `ghost` 变体的用途：往消息里塞表格/卡片等非气泡内容时，
> 用它包一层即可对齐到文字列，而不产生额外的视觉边框。

---

## 八、推荐卡片的编排方式

模板里推荐卡片是这样组织的：

```jsx
<Grid columns={{minWidth: 280}} gap={3}>
  <ClickableCard label="标题" variant="muted" padding={3} onClick={...}>
    <VStack gap={0.5}>
      <Heading level={4}>标题</Heading>
      <Text type="body" color="secondary" size="xsm">描述</Text>
    </VStack>
  </ClickableCard>
</Grid>
```

Vue 版对应：

```vue
<div class="suggestion-grid">          <!-- grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)) -->
  <button v-for="s in suggestions" class="suggestion-card" @click="apply(s.prompt)">
    <strong>{{ s.heading }}</strong>
    <span>{{ s.body }}</span>
  </button>
</div>
```

数据源建议**放在组件外部当常量**（模板里就是 `CATEGORY_SUGGESTIONS` 常量表），
改文案不用动视图逻辑。

---

## 九、验证方法

改完不要只看代码，必须浏览器实测：

```js
// 高度是否撑满
document.querySelector('.ai-panel').getBoundingClientRect().height

// token 是否真的生效
getComputedStyle(el).color
```

弹层/交互需实际点一遍（@提及、滚动到底、发送禁用态）。

---

## 十、坑位提醒

以下都是 [07-pitfalls.md](07-pitfalls.md) 里踩过的，Vue 复刻同样适用：

1. **别写裸 hex / px** —— 一律走 CSS 变量，否则深色模式和主题切换全废
2. **对齐全用 flex 的 align 值** —— astryx 的 `vAlign` 只认 `center`/`end`/`start`/`stretch`，没有 `baseline`
3. **模板体量大，别硬删** —— 只想用一部分时，照骨架重写比删改快得多
4. **生成完看终端最后几行** —— 可能有缺依赖提示（如 `@heroicons/react`）
5. **`ChatLayout` 撑不满高度是常见坑** —— 需要外层给确定高度的 flex 容器

---

## 十一、一句话总结

> astryx 的价值在于**设计决策**（圆角多大、间距几档、气泡多宽），
> 不在于 React 实现。把这些决策抄进 Vue 组件，成本远低于引入双框架。
