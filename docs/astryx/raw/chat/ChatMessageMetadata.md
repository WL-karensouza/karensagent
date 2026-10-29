astryx: answered by CLI 0.7.4 with Core 0.7.4, outside a project
package: @astryxdesign/core

# ChatMessageMetadata

Place ChatMessageMetadata below a message or in the last ChatMessageBubble metadata slot to show a timestamp, footer content, and optional delivery status. Non-rendering scalar slots (booleans and empty strings) create no separator; numeric zero remains visible. Composite React content remains caller-owned.

**Import:** `import {ChatMessageMetadata} from '@astryxdesign/core/Chat';`

## Anatomy

| Element | Required | Description |
|---------|----------|-------------|
| Metadata row | Yes | Sender-aware line containing the visible metadata items. |
| Timestamp | No | Caller-supplied time content at the start of the logical sequence. |
| Footer | No | Caller-supplied information or actions between time and status. |
| Status | No | Localized delivery icon and text when a status is supplied. |

## Best Practices

- **Do:** Put metadata in the last bubble metadata slot when the message uses bubbles, so it follows the bubble content.
- **Do:** Pass timestamp and footer content independently; separators are omitted for non-rendering scalar slots. Composite React nodes are used as supplied.
- **Don't:** Do not supply footer actions without their own accessible names and interaction behavior; the metadata row does not own those controls.
- **Don't:** Do not put the same metadata on both a bubble and its enclosing message.

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `timestamp` | `ReactNode` | - | Timestamp content: a string or Timestamp component. |
| `footer` | `ReactNode` | - | Footer content: model info, reaction buttons, copy button. |
| `status` | `'sending' \| 'sent' \| 'delivered' \| 'read' \| 'error'` | - | Message delivery status. Shows icon + label. |

