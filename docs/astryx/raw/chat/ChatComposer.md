astryx: answered by CLI 0.7.4 with Core 0.7.4, outside a project
package: @astryxdesign/core

# ChatComposer

ChatComposer is the message-entry shell for a chat surface. It coordinates a controlled or uncontrolled draft, provides a default token-capable input and send/stop action, and arranges optional drawer, header, footer, and status content. Custom inputs and send controls can join the same value, submission, disabled, stop, and focus contract through useChatComposerContext().

**Import:** `import {ChatComposer} from '@astryxdesign/core/Chat';`

## Anatomy

| Element | Required | Description |
|---------|----------|-------------|
| Composer frame | Yes | Outer composition root that groups the body with an optional status message above or below it. |
| Composer body | Yes | Rounded, elevated surface containing the header, input, and footer. |
| Drawer | No | Content before the body for attachments or other expandable context, typically ChatComposerDrawer. |
| Header | No | Row for start-aligned actions and end-aligned contextual information. |
| Input | Yes | Default ChatComposerInput or a custom editor connected through useChatComposerContext(). |
| Footer | Yes | Row for caller-supplied footer and send actions plus the primary action. |
| Send or stop action | Yes | Default ChatSendButton or a custom sendButton; it submits the current draft or requests interruption. |
| Status message | No | Error or warning feedback rendered before or after the composer body. |

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `onSubmit` | `(value: string) => void` | - | Called when the user submits a message. **(required)** |
| `onStop` | `() => void` | - | Called when the user requests to stop generation. |
| `isStopShown` | `boolean` | `false` | Whether the stop button is shown instead of the send button. |
| `value` | `string` | - | Controlled input value. |
| `onChange` | `(value: string) => void` | - | Change handler for controlled mode. |
| `placeholder` | `string` | `'Type a message...'` | Placeholder text shown when the input is empty. |
| `isDisabled` | `boolean` | `false` | Disables the composer. |
| `density` | `'compact' \| 'balanced' \| 'spacious'` | `'balanced'` | Visual density. |
| `elevation` | `'none' \| 'low'` | `'low'` | Resting elevation of the composer body. `low` (the default) keeps today's raised look: low at rest, bumping to med on hover / focus. `none` flattens it and draws a border. Keyboard focus in the editor adds the shared focus ring in either presentation; pointer focus does not add that ring. |
| `drawer` | `ReactNode` | - | Slot: collapsible drawer above the input: attachments, context chips, etc. Use ChatComposerDrawer. |
| `headerActions` | `ReactNode` | - | Slot: left-aligned header actions (attach, mention buttons). Use icon-only size="sm" buttons. |
| `headerContext` | `ReactNode` | - | Slot: right-aligned contextual info in the header (context window usage, ProgressBar, supporting text). |
| `input` | `ReactNode` | - | Slot: custom input element. Replaces the default input. Use ChatComposerInput for trigger menus/tokens, or wire any input (plain textarea, rich editor) to the composition contract via useChatComposerContext(): read value/onChange/onSubmit/canSend and register a focus control on inputControlRef so body-click-to-focus works. |
| `footerActions` | `ReactNode` | - | Slot: left-aligned footer actions (model selector, etc). |
| `sendActions` | `ReactNode` | - | Slot: actions to the left of the send button. |
| `sendButton` | `ReactNode` | - | Slot: custom send button. Replaces the default send/stop button. |
| `status` | `{ type: 'error' \| 'warning'; message?: string }` | - | Status message rendered below (or above) the composer. |
| `statusPosition` | `'top' \| 'bottom'` | `'bottom'` | Where to render the status. |

