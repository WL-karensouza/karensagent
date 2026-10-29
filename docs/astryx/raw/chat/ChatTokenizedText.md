astryx: answered by CLI 0.7.4 with Core 0.7.4, outside a project
package: @astryxdesign/core

# ChatTokenizedText

Use ChatTokenizedText inside a chat message when stored plain text contains serialized token values that should be projected as inline badges or caller-rendered token content. Unmatched text is preserved exactly and empty token values are ignored so rendering always finishes.

**Import:** `import {ChatTokenizedText} from '@astryxdesign/core/Chat';`

## Anatomy

| Element | Required | Description |
|---------|----------|-------------|
| Tokenized text | Yes | The inline root that preserves unmatched text and carries the chat-tokenized-text theme target. |
| Rendered token | No | Inline token content rendered by Badge for structured tokens or by the caller for custom tokens. |

## Best Practices

- **Do:** Reuse the same token definitions for composer insertion and message rendering so serialized values and visible labels stay aligned.
- **Do:** Use non-empty, stable serialized values so every definition identifies real message text.
- **Don't:** Use token labels as a substitute for the surrounding message text; the complete message must remain understandable in reading order.
- **Don't:** Put component-owned interaction or accessibility behavior inside a custom token renderer; custom token content remains caller owned.

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `children` | `string` | - | The plain text message containing serialized token values. Patterns matching a token's value are replaced with inline token content. **(required)** |
| `tokens` | `ChatComposerToken[]` | - | Token definitions using the same type as composer input. Each non-empty value is matched literally. Empty values are ignored. Structured tokens render a Badge, while custom tokens render caller content. |
| `xstyle` | `StyleXStyles` | - | StyleX styles for the root text wrapper. Must be a stylex.create() value: not an inline style object like style={{}}. |

## Theming

| Component class | Preferred data attributes | Props | States |
|-----------------|---------------------------|-------|--------|
| `astryx-chat-tokenized-text` | - | - | - |

Override in defineTheme:
```ts
components: {
  'chat-tokenized-text': {
    base: { /* CSS properties */ },
  },
}
```

