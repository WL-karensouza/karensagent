# Astryx Chat 组件速查表

> **用途**：写 AI Chat 界面时的 props 随手查。不用每次跑 CLI。
> **来源**：`npx @astryxdesign/cli component <Name>` 逐条抓取（CLI 0.7.4 / Core 0.7.4）
> **抓取日期**：2026-10-29
> **关联**：PRD §4.5（主界面布局）、§6.1（对话引擎）、§7.3（Astryx 基座）
> ⚠️ 版本仍在 0.x，props 可能变。**改代码前以 CLI 实时输出为准**，本表只管快速回忆。

---

## 0. 一句话

14 个 Chat 组件，**全部从同一个模块导入**：

```ts
import {
  ChatLayout, ChatLayoutScrollButton,
  ChatMessageList, ChatMessage, ChatMessageBubble, ChatMessageMetadata,
  ChatComposer, ChatComposerInput, ChatComposerDrawer,
  ChatSendButton, ChatSystemMessage, ChatToolCalls,
  ChatTokenizedText, ChatDictationButton,
} from '@astryxdesign/core/Chat';
```

**别写成 `@astryxdesign/core/ChatMessage`——会失败。**

---

## 1. 标准组合骨架

```
ChatLayout            ← 外层壳：消息区 + 底部毛玻璃 dock + 自动滚动
├── children: ChatMessageList
│   ├── ChatMessage            (sender="user")
│   │   └── ChatMessageBubble              ← 默认 filled
│   │       └── Markdown
│   └── ChatMessage            (sender="assistant")
│       └── ChatMessageBubble              ← filled / ghost 二选一，见下方说明
│           └── Markdown                   ← AI 回答统一走 Markdown
└── composer: ChatComposer
    ├── input:  ChatComposerInput          ← 默认自带，不用显式传
    └── sendButton: ChatSendButton         ← 默认自带，不用显式传
```

> **`filled` 还是 `ghost`？** 尚未定，属于 UI 验收时再定的细节。
> `filled` 会给助手消息加一层背景色，像传统聊天气泡；`ghost` 透明但保留内边距，像文档式回答。
> **投研场景倾向 `ghost`**——长表格和代码块放在彩色气泡里很难读。但这是设计判断，不是 PRD 规定，**搭骨架时拿两版截图对比再定**。

> **没画进来的三个组件，都是「有能力但本项目不用」**：
> - `ChatToolCalls` —— 决策 20/49，用户界面不展示，只留 dev 开关（见 §5）
> - `ChatSystemMessage` —— 日期分隔，PRD 未要求（见 §6.3）
> - `ChatComposerDrawer` —— 附件区，PRD 未要求（见 §6.3）
>
> 真要用时本文档里都有它的 props，直接查。

**⚠️ `ChatLayout` 不带右侧画布。**
它的 anatomy 只有「消息区 + 底部 dock + 滚动按钮」，没有 artifact panel。
本项目 §4.5 要的「左对话 + 右画布」，**右画布来自 `ai-chat` 模板自带的可调宽 panel 结构**，`ChatLayout` 塞进左半边即可。

---

## 2. 布局层

### ChatLayout

| Prop | 类型 | 默认 | 说明 |
|---|---|---|---|
| `children` | `ReactNode` | — | **必填**。通常放 `ChatMessageList` |
| `composer` | `ReactNode` | — | **必填**。通常放 `ChatComposer`，固定在底部毛玻璃 dock |
| `emptyState` | `ReactNode` | — | 无消息时居中显示。配合 `EmptyState` 组件 |
| `scrollButton` | `ReactNode \| null` | 默认滚动按钮 | 传 `null` 隐藏 |
| `scrollRef` | `RefObject<HTMLElement \| null>` | — | 聊天嵌在会滚动的父容器里时，把父容器 ref 传进来 |
| `density` | `'compact' \| 'balanced' \| 'spacious'` | `balanced` | 控制 dock 内边距、消息区最大宽度、毛玻璃层高度 |

> **坑**：不要给 ChatLayout 设固定高度，让 `flex: 1` 撑满；同一滚动容器里别放两个 ChatLayout。

### ChatLayoutScrollButton

| Prop | 类型 | 说明 |
|---|---|---|
| `isVisible` | `boolean` | **必填**。绑滚动位置判断 |
| `label` | `string` | 展开成带文字按钮（如「有新消息」） |
| `onClick` | `() => void` | **必填**。滚到底并清未读标记 |

---

## 3. 消息层

### ChatMessageList

| Prop | 类型 | 默认 | 说明 |
|---|---|---|---|
| `children` | `ReactNode` | — | **必填**。`ChatMessage` / `ChatSystemMessage` |
| `emptyState` | `ReactNode` | — | 空列表内容 |
| `isStreaming` | `boolean` | `false` | **★ 流式必备**。设 log 的 `aria-busy`，屏幕阅读器等整段结束后念一次，不会逐 token 念 |
| `gap` | `0 \| 0.5 \| 1 \| 1.5 \| 2 \| 3 \| 4 \| 5 \| 6 \| 8 \| 10` | 跟随 density | 行间距 |
| `align` | `'top' \| 'bottom'` | `bottom` | 列表不满时贴底（短对话贴着输入框）还是贴顶 |
| `scrollToTopAction` | `() => Promise<void>` | — | 滚到顶触发，用于加载更早消息，自动显示 spinner |
| `density` | `'compact' \| 'balanced' \| 'spacious'` | `balanced` | 通过 context 传给子消息 |

### ChatMessage

| Prop | 类型 | 默认 | 说明 |
|---|---|---|---|
| `sender` | `'user' \| 'assistant' \| 'system'` | — | **必填**。决定对齐方式和布局 |
| `children` | `ReactNode` | — | **必填**。气泡、工具调用、图片等 |
| `avatar` | `ReactNode` | — | 头像，通常传 `Avatar` |
| `name` | `ReactNode` | — | 发送者名。**仅当第一个子元素不是气泡时用**；是气泡就放气泡的 `name` |
| `metadata` | `ReactNode` | — | 底部元信息。**仅当最后一个子元素不是气泡时用** |
| `density` | `'compact' \| 'balanced' \| 'spacious'` | 继承列表 | 密度 |

### ChatMessageBubble

| Prop | 类型 | 默认 | 说明 |
|---|---|---|---|
| `children` | `ReactNode` | — | **必填**。文字、`Markdown` 或任意节点 |
| `variant` | `'filled' \| 'ghost'` | `filled` | `filled` 带发送方配色的背景；`ghost` 透明但有内边距，**用来让宽内容（图表、卡片）对齐到文字列** |
| `name` | `ReactNode` | — | 气泡上方名字，放在**第一个**气泡上 |
| `metadata` | `ReactNode` | — | 气泡下方元信息，放在**最后一个**气泡上 |
| `group` | `'first' \| 'middle' \| 'last'` | — | 同发送方连发多条时，用来压角半径 |
| `width` | `SizeValue` | `max(80%, 280px)` | 数字=px，字符串原样用。配 `variant="ghost"` 让产物卡片占满整列 |

### ChatMessageMetadata

| Prop | 类型 | 说明 |
|---|---|---|
| `timestamp` | `ReactNode` | 时间，可传 `Timestamp` 组件 |
| `footer` | `ReactNode` | 复制按钮、模型名、反馈按钮等 |
| `status` | `'sending' \| 'sent' \| 'delivered' \| 'read' \| 'error'` | 送达状态，带图标 + 文案 |

> **坑**：同一份 metadata 别既挂在气泡又挂在 ChatMessage 上。

### ChatSystemMessage

| Prop | 类型 | 默认 | 说明 |
|---|---|---|---|
| `children` | `ReactNode` | — | **必填**。状态提示或分隔标题 |
| `variant` | `'default' \| 'divider'` | `default` | `divider` 两侧带横线，用于日期 / 章节分隔 |
| `icon` | `ReactNode` | — | 仅 `default` 变体渲染 |

---

## 4. 输入层

### ChatComposer

| Prop | 类型 | 默认 | 说明 |
|---|---|---|---|
| `onSubmit` | `(value: string) => void` | — | **必填**。提交消息 |
| `onStop` | `() => void` | — | 停止生成。**决策 38 用的就是这个** |
| `isStopShown` | `boolean` | `false` | 停止态显示停止按钮而非发送按钮 |
| `value` / `onChange` | `string` / `(v: string) => void` | — | 受控模式 |
| `placeholder` | `string` | `'Type a message...'` | 占位文案 |
| `isDisabled` | `boolean` | `false` | 禁用整个输入区 |
| `density` | `'compact' \| 'balanced' \| 'spacious'` | `balanced` | 密度 |
| `elevation` | `'none' \| 'low'` | `low` | `low` 悬浮抬起，`none` 扁平化改描边 |
| `drawer` | `ReactNode` | — | 输入框上方的可折叠抽屉（附件、上下文 chip） |
| `headerActions` | `ReactNode` | — | 头部左对齐动作（附件、@ 按钮），用 `size="sm"` 图标按钮 |
| `headerContext` | `ReactNode` | — | 头部右对齐信息（上下文用量、ProgressBar） |
| `input` | `ReactNode` | 默认 `ChatComposerInput` | 换自定义输入框 |
| `footerActions` | `ReactNode` | — | 底部左对齐动作（模型选择器） |
| `sendActions` | `ReactNode` | — | 发送按钮左侧的动作（语音按钮放这） |
| `sendButton` | `ReactNode` | 默认 `ChatSendButton` | 换自定义发送按钮 |
| `status` | `{ type: 'error' \| 'warning'; message?: string }` | — | 输入区下方/上方状态提示 |
| `statusPosition` | `'top' \| 'bottom'` | `bottom` | 状态提示位置 |

### ChatComposerInput

| Prop | 类型 | 默认 | 说明 |
|---|---|---|---|
| `value` / `onChange` | `string` / `(v: string) => void` | — | 受控模式 |
| `onSubmit` | `(value: string) => void` | — | Enter（不带 Shift）提交，Shift+Enter 换行 |
| `placeholder` | `string` | `'Type a message...'` | 占位 |
| `maxRows` | `number` | `8` | 超过就内部滚动 |
| `triggers` | `ChatComposerTrigger[]` | — | **★ `@` 或 `/` 触发的候选菜单**。每项含触发字符、搜索源、`onSelect`。含空格的候选要设 `hasMultiWordQuery: true` |
| `debounceMs` | `number` | `150` | 异步搜索防抖 |
| `hasHistory` | `boolean` | `true` | 上下方向键调出历史消息 |
| `label` | `string` | `'Message input'` | 屏幕阅读器标签 |
| `isDisabled` | `boolean` | `false` | 流式期间可禁用 |
| `onPaste` | `(event, text) => boolean \| void` | — | 返回 `true` 表示自己处理 |
| `pasteAsToken` | `useChatPasteAsToken()` 返回值 \| `false` | 默认 >200 字变 token | 长文本粘贴自动折叠成可展开 token |
| `onFiles` | `(files: File[]) => void` | — | 粘贴或拖入文件 |
| `onKeyDown` | `(event) => void` | — | 内建 Enter 行为之前触发。`preventDefault()` 可拦掉默认提交 |
| `handleRef` | `Ref<ChatComposerInputHandle>` | — | 命令式操作：`insertToken` / `insertText` / `focus` / `getValue` |

### ChatComposerDrawer

| Prop | 类型 | 默认 | 说明 |
|---|---|---|---|
| `children` | `ReactNode` | — | **必填**。token、chip、预览 |
| `count` | `number` | — | 传了才出现折叠/展开开关，显示在徽章上 |
| `label` | `string` | `'Items'` | 折叠摘要旁的标签，**用具体复数名词**（"Attachments"） |
| `collapsedSummary` | `ReactNode` | 默认徽章 | 自定义折叠态外观 |
| `isCollapsed` / `defaultIsCollapsed` / `onCollapsedChange` | `boolean` / `boolean` / `(b) => void` | `false` | 受控 / 非受控折叠状态 |

### ChatSendButton

| Prop | 类型 | 默认 | 说明 |
|---|---|---|---|
| `isStopShown` | `boolean` | 取自 context | 显示停止态 |
| `isDisabled` | `boolean` | `!canSend` | **只影响发送态，不影响停止态** |
| `onSend` / `onStop` | `() => void` | 取自 context | 在 Composer 内可省略 |
| `sendIcon` / `stopIcon` | `ReactNode` | 内置图标 | 自定义图标 |
| `size` | `'sm' \| 'md'` | `md` | 尺寸 |

### ChatDictationButton（语音输入，v1 大概率不用）

| Prop | 类型 | 默认 | 说明 |
|---|---|---|---|
| `dictation` | `useChatDictation()` 返回值 | — | **必填** |
| `size` | `'sm' \| 'md'` | `md` | 尺寸 |
| `isHiddenWhenUnsupported` | `boolean` | `true` | 浏览器不支持 SpeechRecognition 时自动隐藏 |
| `label` | `string` | 按状态自动 | 无障碍标签 |

---

## 5. 内容层

### ChatToolCalls　（仅 dev 调试视图使用，用户界面不展示）

> **2026-10-29 定案：默认不展示。**
> 决策 20 明确「调了什么工具不展示」，决策 14 又取消了前端溯源展示——产品两次否掉管道可见性。
> 但排查「这个数据为什么查不到」时需要看取证链，所以**保留为 dev-only 开关**（`?debug=1` 或环境变量控制），用户态渲染分支里不出现。

| Prop | 类型 | 说明 |
|---|---|---|
| `calls` | `ChatToolCallItem[]` | **必填**。传 1 条就内联渲染；多条自动折叠成摘要，最新一条露在表面 |
| `label` | `string` | 展开后的自定义摘要标题 |
| `isExpanded` / `defaultIsExpanded` / `onExpandedChange` | `boolean` / `boolean` / `(b) => void` | 受控 / 非受控展开状态 |
| `xstyle` | `StyleXStyles` | 必须是 `stylex.create()` 的值，不能传 `style={{}}` |

**`ChatToolCallItem` 字段**

| 字段 | 说明 |
|---|---|
| `name` | 工具名，等宽字体显示（`bash`、`web_search`） |
| `status` | **`'pending' \| 'running' \| 'complete' \| 'error'`**，不传默认 `complete` |
| `target` | 作用对象：文件路径、命令、搜索词 |
| `duration` | 执行耗时，显示在尾部 |
| `node` | 运行环境徽章（如 `workspace`） |
| `additions` / `deletions` | 编辑类操作的增删行数 |
| `stats` | 补充统计 |
| `errorMessage` | 失败原因 |
| `resultDetail` | 结果详情，可放代码块 |
| `key` | **流式时必须给唯一 key**，否则已完成行会被重挂载 |
| `data` | 透传数据 |

> **dev 视图里怎么用**：把编排层每个取数步骤映射成一条 call——`status` 对应执行状态，`target` 填「股票代码 + 数据源」，`errorMessage` 填失败原因。
> 仅在 `import.meta.env.DEV` 或调试开关打开时渲染，生产用户态不挂这个组件。

### ChatTokenizedText

| Prop | 类型 | 说明 |
|---|---|---|
| `children` | `string` | **必填**。含序列化 token 占位符的纯文本 |
| `tokens` | `ChatComposerToken[]` | token 定义，**和输入框用同一份**，保证序列化值一致 |

> 用途：想让「这只票」这类实体在历史消息里也能高亮成可点徽章时用。

### useStreamingText（hook，不是组件 —— 导入路径不同！）

```ts
import {useStreamingText} from '@astryxdesign/core/hooks';
```

**它解决的问题**：把「一阵一阵蹦出来」的流式文本，抹平成逐字匀速显现。
用 `requestAnimationFrame` 驱动，**在词边界和 markdown 语法边界处才推进**，所以不会把 `**粗体` 切成半个语法导致渲染错乱。

| 参数（从官方最佳实践反推，CLI 未列完整签名） | 说明 |
|---|---|
| `targetText` | **传累积后的全文**，不是单个 chunk——内部自己做增量显现 |
| `isStreaming` | 流结束时设 `false`，会**直接跳到完整文本** |
| `speed` | `'instant'` 用于不需要动画的场景（搜索结果、用户开了减弱动效） |

> **为什么这条对本项目关键**：§6.1 是 SSE 推送，token 到达节奏天然不均匀。不抹平的话，模型吐得快时字是「跳」出来的。
> 配合 `ChatMessageList.isStreaming`（管无障碍朗读节奏）+ `useStreamingText`（管视觉显现节奏），两者分工不同，**两个都要设**。

---

## 6. 本项目落地映射

### 6.1 PRD 有明确要求的（可直接开工）

| PRD 条款 | 用哪个 prop / 组件 | 备注 |
|---|---|---|
| §6.1 流式回答 | `ChatMessageList.isStreaming` + `useStreamingText`（**两个都设**） | 前者管屏幕阅读器朗读节奏，后者管视觉逐字显现 |
| 决策 38 停止生成 | `ChatComposer.onStop` + `isStopShown` | PRD 原文就指定用这个，不自造 |
| §1.4 原则一 占位符文本渲染 | `Markdown` 组件 | 官方描述明确写用于 AI responses |
| §4.5 右画布外壳 | `ai-chat` **模板**的 panel 结构 | `ChatLayout` 不自带画布，见本文 §1 |
| 决策 14 不做溯源 | **不引** `Citation` | 组件存在但不用 |
| 决策 20 不展示工具调用 | **不挂** `ChatToolCalls`（除 dev 开关） | 见本文 §5 说明 |

### 6.2 §4.5 的三条硬规则——模板不提供，必须自己写

`ai-chat` 模板给的是「可拖拽分栏」这个壳，**下面三条业务逻辑全要自己实现**：

| 规则 | 实现要点 |
|---|---|
| **本次回答纯文字 → 右边不出现，对话占满整宽** | 由 `ui_spec` 判断本轮有无可视化块，无则整列不渲染右面板 |
| **产物最多钉 2 个，手动钉，系统不自动** | 画布顶部钉住区，切换逻辑自建 |
| **会话结束即清空** | 与 §6.4 短期记忆一致，退出会话清掉画布产物 |

> **§4.3 的生成式 UI 与 Chat 组件无关**：`KLineChart` / `PeerCompare` 这些业务组件由 `web/ui/` 的渲染器挂到右画布，
> **不塞进聊天气泡**（§4.5 硬规则：左边只放自然语言，绝不放图表本体）。
> 所以 `ChatMessageBubble` 的 `variant="ghost"` + `width` 在本项目**用不上**。

### 6.3 PRD 没要求、但组件白给的（可选增量，别当需求）

> 下面这些**不是 PRD 需求**。记在这里只是因为实现成本接近零，将来想加时不用重新调研。
> **默认不做**，除非王磊哥哥明确说要。

| 能力 | 组件 / prop | 备注 |
|---|---|---|
| 股票 `@` 提及 | `ChatComposerInput.triggers` | 觉得手打股票代码烦时再加 |
| 长文本粘贴折叠成 token | `ChatComposerInput.pasteAsToken` | **默认已开**（>200 字），不用做事 |
| 上下键调出历史消息 | `ChatComposerInput.hasHistory` | **默认已开**，不用做事 |
| 日期分隔 | `ChatSystemMessage variant="divider"` | 会话拉很长、需要按天切分时 |
| 语音输入 | `ChatDictationButton` + `useChatDictation` | 不太可能用 |

### 6.4 一条容易搞错的层次

**「数据查不到」不是 `ChatComposer.status`。**

| 场景 | 正确落点 |
|---|---|
| 数据源三层全败 → 对用户说「这个查不到」 | ✅ **回答正文**的【未知】区块（§1.4 原则二、§8.3） |
| 问题压根没发出去（网络断、超时） | ✅ `ChatComposer.status` + `statusPosition` |

`ChatComposer.status` 是**输入区级**的错误条，不是回答内容。混用会把「数据缺失」降级成「操作失败」，破坏三色分离。

---

## 7. 三条铁律

1. **组件导入路径只用 `@astryxdesign/core/Chat`**，符号用组件名。**但 hook 不在这里**——`useStreamingText` 等一律从 `@astryxdesign/core/hooks` 导入。
2. **任何 props 拿不准就跑 CLI**：`npx @astryxdesign/cli component ChatComposer`。本表是 0.7.4 的快照，会过时。
3. **`xstyle` 只吃 `stylex.create()` 的结果**，传 `style={{}}` 会报错。本项目走接入模式 A（不上 StyleX），所以**这几个 `xstyle` prop 一律不用**，改用外层容器控制间距。
