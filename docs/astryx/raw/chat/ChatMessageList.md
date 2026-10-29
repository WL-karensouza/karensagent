astryx: answered by CLI 0.7.4 with Core 0.7.4, outside a project
package: @astryxdesign/core

# ChatMessageList

Presentational message container with density context and infinite scroll support. Provides role="log" with aria-live="polite" for accessibility. A flex spacer pushes messages to the bottom when the list isn't full; set align="top" to start messages at the top instead.

**Import:** `import {ChatMessageList} from '@astryxdesign/core/Chat';`

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `children` | `ReactNode` | - | Message elements: typically ChatMessage or ChatSystemMessage. **(required)** |
| `emptyState` | `ReactNode` | - | Content shown when the list has no messages. |
| `scrollToTopAction` | `() => Promise<void>` | - | Async action fired when user scrolls to top. Use for loading older messages. Wrapped in useTransition: shows a spinner at the top while pending. |
| `density` | `'compact' \| 'balanced' \| 'spacious'` | `'balanced'` | Visual density: flows to child messages via context. |
| `gap` | `0 \| 0.5 \| 1 \| 1.5 \| 2 \| 3 \| 4 \| 5 \| 6 \| 8 \| 10` | - | Gap between top-level message rows. Defaults to the selected density; override for LLM event streams or independent rows that need different spacing from density. |
| `align` | `'top' \| 'bottom'` | `'bottom'` | Vertical alignment when the list is shorter than its container. 'bottom' fills free space with a spacer so short conversations sit above the composer; 'top' omits the spacer so messages start at the top. Only affects a non-full list; overflowing lists scroll identically, preserving auto-scroll-to-bottom. |
| `isStreaming` | `boolean` | `false` | Whether an assistant message is actively streaming. Marks the log aria-busy so screen readers wait and announce the completed message once instead of re-announcing partial text on every token. |

