# 04 · 组件（173 个）与导入陷阱

> 2026-10-29 用 `component` 实测。原始输出见 `raw/astryx-components.txt`。

---

## ⚠️ 最重要的一条：74 个组件的模块路径和名字不一样

`component` 列表里的 `import:` 给的是**模块路径**，导出的符号名仍然是组件名本身。

```ts
// ✅ 正确：符号用名字，路径用模块
import { TableRow } from '@astryxdesign/core/Table'
import { ChatMessage } from '@astryxdesign/core/Chat'

// ❌ 错误：按名字拼路径，直接 import 失败
import { TableRow } from '@astryxdesign/core/TableRow'
```

### 高频对照

| 组件 | 从哪个模块导入 |
|---|---|
| 全部 14 个 `Chat*` | `@astryxdesign/core/Chat` |
| `Table*` 全家（Row/Cell/Header/Body/Footer/SelectionToolbar） | `@astryxdesign/core/Table` |
| `Tab` · `TabMenu` | `@astryxdesign/core/TabList` |
| `LayoutHeader/Content/Footer/Panel` | `@astryxdesign/core/Layout` |
| `SideNavItem/Section/Heading/CollapseButton` | `@astryxdesign/core/SideNav` |
| `TopNavItem/Menu/MegaMenu/Heading` | `@astryxdesign/core/TopNav` |
| `DropdownMenuItem/Group/SubMenu/Divider` | `@astryxdesign/core/DropdownMenu` |
| `CommandPaletteItem/List/Input/Group/Footer/Empty` | `@astryxdesign/core/CommandPalette` |
| `Step` | `@astryxdesign/core/Stepper` |
| `BreadcrumbItem` | `@astryxdesign/core/Breadcrumbs` |
| `ListItem` | `@astryxdesign/core/List` |
| `GridSpan` | `@astryxdesign/core/Grid` |
| `AvatarStatusDot` · `AvatarGroupOverflow` | `@astryxdesign/core/Avatar` / `AvatarGroup` |
| `Theme` · `MediaTheme` | `@astryxdesign/core/theme`（**小写**） |
| `InternationalizationProvider` | `@astryxdesign/core/i18n` |

**铁律**：写 import 前跑一次 `npx @astryxdesign/cli component <Name>`，把输出的 `**Import:**` 整行照抄。

### hooks 不在组件目录

```ts
import { useStreamingText } from '@astryxdesign/core/hooks'
```

`useStreamingText`、`useChatDictation` 这类的入口是 `@astryxdesign/core/hooks`，不是 `Chat`。

---

## 组件分组速查（按做前端会用到的）

| 层 | 组件 |
|---|---|
| **布局** | `Layout` · `LayoutHeader` · `LayoutContent` · `LayoutFooter` · `LayoutPanel` · `VStack` · `HStack` · `Stack` · `Grid` · `GridSpan` · `Section` · `Center` · `Divider` · `ScrollableArea` · `AppShell` |
| **文本** | `Text` · `Heading` · `Markdown` · `List` · `Code` · `CodeBlock` · `Blockquote` · `Link` · `Citation` · `Kbd` |
| **表格** | `Table` · `TableHeader` · `TableHeaderCell` · `TableBody` · `TableRow` · `TableCell` · `TableFooter` · `TableSelectionToolbar` |
| **对话（14）** | `ChatLayout` · `ChatLayoutScrollButton` · `ChatMessageList` · `ChatMessage` · `ChatMessageBubble` · `ChatMessageMetadata` · `ChatComposer` · `ChatComposerInput` · `ChatComposerDrawer` · `ChatSendButton` · `ChatSystemMessage` · `ChatToolCalls` · `ChatTokenizedText` · `ChatDictationButton` |
| **输入** | `TextInput` · `TextArea` · `NumberInput` · `DateInput` · `DateRangeInput` · `TimeInput` · `Selector` · `MultiSelector` · `ComplexSelector` · `CheckboxInput` · `CheckboxList` · `RadioList` · `Switch` · `Slider` · `ToggleButton` · `ToggleButtonGroup` · `Typeahead` · `FileInput` · `Tokenizer` |
| **展示** | `Card` · `ClickableCard` · `MetadataList` · `Badge` · `StatusDot` · `ProgressBar` · `Avatar` · `AvatarGroup` · `Thumbnail` · `Carousel` · `AspectRatio` · `Skeleton` · `Spinner` · `EmptyState` · `Icon` · `Overlay` · `Lightbox` |
| **反馈** | `Toast` · `Banner` · `AlertDialog` · `Dialog` · `DialogHeader` · `Drawer` · `DrawerHeader` · `Popover` · `HoverCard` · `Tooltip` · `BottomSheet` |
| **导航** | `TopNav` · `SideNav` · `Breadcrumbs` · `TabList` · `Tab` · `Pagination` · `CommandPalette` · `ContextMenu` · `DropdownMenu` · `MoreMenu` · `MobileNav` · `Outline` · `TreeList` |
| **高级 / 组合** | `Calendar` · `Timestamp` · `Timer` · `Token` · `Toolbar` · `SegmentedControl` · `PowerSearch` · `FileExplorer` 相关块 · `Theme` · `InternationalizationProvider` |
| **无技能区** | ⚠️ **没有图表组件**。grep `chart`/`plot`/`graph`/`spark`/`axis`/`legend` 零命中。最接近可视化的是 `ProgressBar` 和 `StatusDot` |

---

## 关键提醒

1. **`Badge` 只用于计数**（Astryx 官方规矩），不要拿它当标签/彩色块。
2. **密集数据用行，不用卡片套**：`Table` / `List`/`Item` 优先于 `Card` 列表。
3. **`Citation` 有，但要不要用是产品决定**——它是「引用来源」展示，适合需要溯源的场景。
4. **`Markdown` 组件明确为 AI 回答设计**，会处理标题、列表、表格、代码块、引用。
