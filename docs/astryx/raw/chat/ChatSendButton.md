astryx: answered by CLI 0.7.4 with Core 0.7.4, outside a project
package: @astryxdesign/core

# ChatSendButton

Use ChatSendButton as ChatComposer’s send control when the action should switch between sending and stopping. Inside ChatComposer it reads readiness, streaming state, and action callbacks from context; standalone usage supplies those values explicitly.

**Import:** `import {ChatSendButton} from '@astryxdesign/core/Chat';`

## Anatomy

| Element | Required | Description |
|---------|----------|-------------|
| Action button | Yes | Circular icon-only Button that exposes the translated Send or Stop name and carries the chat-send-button theme target. |

## Best Practices

- **Do:** Place ChatSendButton inside ChatComposer when its readiness and send or stop lifecycle should follow composer context.
- **Do:** For standalone use, provide the state and matching onSend or onStop callback explicitly.
- **Do:** Keep the translated Send or Stop accessible name intact when supplying custom icon artwork; the icon is decorative and must not be the only name source.
- **Don't:** Do not render the stop state without a working onStop callback from props or ChatComposer context.
- **Don't:** Do not expect isDisabled to disable the stop action; it applies only to the send state.

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `isStopShown` | `boolean` | - | Whether the stop button is shown. Defaults to context value. |
| `isDisabled` | `boolean` | - | Whether the send button is disabled. Defaults to !canSend from context. |
| `onSend` | `() => void` | - | Called when the user clicks send. Defaults to context onSubmit. |
| `onStop` | `() => void` | - | Called when the user clicks stop during streaming. Defaults to context onStop. |
| `sendIcon` | `ReactNode` | - | Custom icon for the send state. Defaults to arrowUp from icon registry. |
| `stopIcon` | `ReactNode` | - | Custom icon for the stop state. Defaults to stop from icon registry. |
| `size` | `'sm' \| 'md'` | `'md'` | Button size. |
| `xstyle` | `StyleXStyles` | - | StyleX styles for layout customization (margins, positioning, sizing). Must be a stylex.create() value: not an inline style object like style={{}}. |

