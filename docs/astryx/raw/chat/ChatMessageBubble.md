astryx: answered by CLI 0.7.4 with Core 0.7.4, outside a project
package: @astryxdesign/core

# ChatMessageBubble

Styled content container for the chat "bubble." Reads sender from parent ChatMessage context to auto-style the background. Use filled for standard messages and ghost when content needs alignment without a visible boundary. Supports name/metadata slots aligned with bubble padding, and multi-bubble grouping via the group prop for consecutive messages from the same sender.

**Import:** `import {ChatMessageBubble} from '@astryxdesign/core/Chat';`

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `children` | `ReactNode` | - | Bubble content: text, Markdown, or any ReactNode. **(required)** |
| `variant` | `'filled' \| 'ghost'` | `'filled'` | Visual variant. 'filled' renders sender-colored background (default). 'ghost' renders transparent background but keeps padding for alignment. |
| `name` | `ReactNode` | - | Sender name rendered above the bubble, aligned with bubble text padding. Use on the first bubble in a message. Non-rendering scalar values (null, undefined, booleans, and the empty string) omit the aligned wrapper; numeric 0 remains aligned. If the first content is raw (no bubble), use ChatMessage's `name` prop instead. |
| `metadata` | `ReactNode` | - | Metadata content rendered below the bubble, aligned with bubble text padding. Use on the last bubble in a message. Non-rendering scalar values (null, undefined, booleans, and the empty string) omit the aligned wrapper; numeric 0 remains aligned. If the last content is raw (no bubble), use ChatMessage's `metadata` prop instead. |
| `group` | `'first' \| 'middle' \| 'last'` | - | Position within a multi-bubble group. Controls corner radius reduction on the sender side. Leave unset for standalone bubbles (full radius). |
| `width` | `SizeValue` | - | Width of the bubble (number = pixels, string = used as-is). When set, replaces the default max(80%, 280px) width cap. Combine with variant="ghost" to let custom content (an artifact card, attachments) span the full message column. |

