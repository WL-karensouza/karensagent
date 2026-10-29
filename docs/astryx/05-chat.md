# 05 · Chat 组件速查（做对话界面必读）

> 14 个组件**全部从同一个模块导入**：
>
> ```ts
> import {
>   ChatLayout, ChatLayoutScrollButton,
>   ChatMessageList, ChatMessage, ChatMessageBubble, ChatMessageMetadata,
>   ChatComposer, ChatComposerInput, ChatComposerDrawer,
>   ChatSendButton, ChatSystemMessage, ChatToolCalls,
>   ChatTokenizedText, ChatDictationButton,
> } from '@astryxdesign/core/Chat'
> ```
>
> 完整 props 见 `raw/chat/` 下每个组件一份的原文。

---

## 标准组合骨架

```
ChatLayout                       ← 外壳：消息区 + 底部毛玻璃 dock + 自动滚动
├── children: ChatMessageList
│   ├── ChatMessage (sender="user")
│   │   └── ChatMessageBubble
│   └── ChatMessage (sender="assistant")
│       └── ChatMessageBubble variant="ghost"   ← 自定义内容（表格、区块）
└── composer: ChatComposer
    ├── input:  ChatComposerInput   （默认自带，需要 @ 提及才显式传）
    └── sendButton: ChatSendButton  （默认自带）
```

⚠️ **`ChatLayout` 不自带侧边画布**。要「左对话 + 右面板」，得自己在外层做分栏，把 `ChatLayout` 塞进左半边。

---

## 布局层

| 组件 | 关键 props |
|---|---|
| **ChatLayout** | `children`(必填) · `composer`(必填) · `emptyState` · `scrollButton`（传 `null` 隐藏） · `scrollRef`（嵌在会滚动的父容器里时用） · `density` |
| **ChatLayoutScrollButton** | `isVisible`(必填) · `label` · `onClick`(必填) |

> **坑**：`ChatLayout` 靠 `flex:1` 撑满父容器。如果外层是 `display:contents`（Astryx 的 `Theme` 包装器就是），高度传不下来 → 界面只占内容高度。
> **解法**：外面套一层给定高度的 flex 容器（如 `<VStack style={{height:'100%'}}>`）。

---

## 消息层

| 组件 | 关键 props |
|---|---|
| **ChatMessageList** | `children`(必填) · `emptyState` · `isStreaming`（设 `aria-busy`，屏幕阅读器等整段结束再念） · `gap` · `align`（`top`/`bottom`） · `scrollToTopAction` · `density` |
| **ChatMessage** | `sender`(必填，`user`/`assistant`/`system`) · `children` · `avatar` · `name` · `metadata` · `density` |
| **ChatMessageBubble** | `children`(必填) · `variant`(`filled`/`ghost`) · `name` · `metadata` · `group`(`first`/`middle`/`last`) · `width` |
| **ChatMessageMetadata** | `timestamp` · `footer` · `status`(`sending`/`sent`/`delivered`/`read`/`error`) |
| **ChatSystemMessage** | `children` · `variant`(`default`/`divider`) · `icon` |

> `ghost` 变体 = 透明底但保留内边距，适合往消息里塞**非气泡内容**（表格、自定义区块、卡片）。
> 自定义（非气泡）子内容默认贴消息边缘，用 `ChatMessageBubble variant="ghost"` 包一层即可对齐文字列。

---

## 输入层

| 组件 | 关键 props |
|---|---|
| **ChatComposer** | `onSubmit`(必填) · `onStop` · `isStopShown` · `value`/`onChange` · `placeholder` · `isDisabled` · `density` · `elevation` · `drawer` · `headerActions` · `headerContext` · `input` · `footerActions` · `sendActions` · `sendButton` · `status` · `statusPosition` |
| **ChatComposerInput** | `value`/`onChange` · `onSubmit` · `placeholder` · `maxRows`(默认 8) · `triggers`（`@`/`/` 候选菜单） · `debounceMs` · `hasHistory` · `isDisabled` · `onPaste` · `pasteAsToken`（默认 >200 字变 token） · `onFiles` · `onKeyDown` · `handleRef` |
| **ChatComposerDrawer** | `children`(必填) · `count`（传了才有折叠开关） · `label` · `collapsedSummary` · `isCollapsed`/`defaultIsCollapsed`/`onCollapsedChange` |
| **ChatSendButton** | `isStopShown` · `isDisabled` · `onSend` · `onStop` · `sendIcon`/`stopIcon` · `size` |
| **ChatDictationButton** | `dictation`(必填，`useChatDictation()` 返回值) · `size` · `isHiddenWhenUnsupported` · `label` |

> **停止生成**：`ChatComposer` 同时传 `onStop` 和 `isStopShown`，按钮自动在「发送 ↔ 停止」之间切换。
> `ChatSendButton.isDisabled` **只影响发送态，不影响停止态**。

---

## 内容层

| 组件 | 关键 props |
|---|---|
| **ChatToolCalls** | `calls`(必填) · `label` · `isExpanded`/`defaultIsExpanded`/`onExpandedChange` |
| **ChatTokenizedText** | `children`(必填，string) · `tokens` |

`ChatToolCallItem` 字段：`name` · `status`(`pending`/`running`/`complete`/`error`) · `target` · `duration` · `node` · `additions`/`deletions` · `stats` · `errorMessage` · `resultDetail` · `key`（**流式时必填唯一 key**） · `data`

---

## Hook：useStreamingText

```ts
import { useStreamingText } from '@astryxdesign/core/hooks'
```

把「一阵一阵蹦出来」的流式文本抹平成逐字匀速显现。
用 `requestAnimationFrame` 驱动，**在词边界和 markdown 语法边界才推进**，不会把 `**粗体` 切成半个语法。

| 参数 | 说明 |
|---|---|
| `targetText` | **传累积后的全文**，不是单个 chunk |
| `isStreaming` | 流结束设 `false`，会**直接跳到完整文本** |
| `speed` | `'instant'` 用于不需要动画的场景（搜索结果 / 减弱动效） |

> **两个 isStreaming 分工不同，都要设**：
> `ChatMessageList.isStreaming` 管无障碍朗读节奏（等整段结束再念一次）；
> `useStreamingText.isStreaming` 管视觉显现节奏。
