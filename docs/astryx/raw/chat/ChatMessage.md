astryx: answered by CLI 0.7.4 with Core 0.7.4, outside a project
package: @astryxdesign/core

# ChatMessage

Sender context wrapper: handles avatar, name, metadata, and alignment based on sender role.

**Import:** `import {ChatMessage} from '@astryxdesign/core/Chat';`

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `sender` | `'user' \| 'assistant' \| 'system'` | - | Who sent this message: controls alignment and layout. **(required)** |
| `children` | `ReactNode` | - | Free-form content: bubbles, asset lists, tool calls, images. Custom (non-bubble) children render flush with the message edge; wrap them in a ghost ChatMessageBubble to align them with the bubble text column. **(required)** |
| `avatar` | `ReactNode` | - | Avatar element rendered beside the message. Typically Avatar. `null`, booleans, and empty strings create no slot; any other content that renders nothing collapses its slot. |
| `name` | `ReactNode` | - | Sender name rendered above the message body; it labels the message. `null`, booleans, and empty strings create no slot, and any other content that renders nothing collapses its slot; either way the message is labelled by the translated sender fallback. Use when the first child is raw content (not a bubble). If the first child is a bubble, put the name on the bubble's `name` prop instead. |
| `metadata` | `ReactNode` | - | Metadata rendered below the message body. `null`, booleans, and empty strings create no slot; any other content that renders nothing collapses its slot. Use when the last child is raw content (not a bubble). If the last child is a bubble, put metadata on the bubble's `metadata` prop instead. |
| `density` | `'compact' \| 'balanced' \| 'spacious'` | `'balanced'` | Visual density. Inherited from list context if not set. |

