astryx: answered by CLI 0.7.4 with Core 0.7.4, outside a project
package: @astryxdesign/core

# ChatDictationButton

ChatDictationButton is a toggle button that starts and stops voice dictation inside a chat composer. It pairs with useChatDictation to show a microphone icon when idle and animated frequency bars when listening. Place it in the sendActions slot of ChatComposer.

**Import:** `import {ChatDictationButton} from '@astryxdesign/core/Chat';`

## Anatomy

| Element | Required | Description |
|---------|----------|-------------|
| Microphone icon | Yes | Shown in the idle state. Indicates that tapping will start voice input. |
| Frequency bars | No | Animated equalizer bars that replace the icon during listening. React to real microphone volume. |
| Ghost button | Yes | The underlying Button with ghost variant and isIconOnly, providing the hit target and focus ring. |

## Best Practices

- **Do:** Place the dictation button in the sendActions slot of ChatComposer so it sits next to the send button where users expect voice input controls.
- **Do:** Pass an inputRef to useChatDictation so interim transcripts appear as ghost text in the composer input while the user speaks.
- **Do:** Enable hasSounds on useChatDictation to give users audio feedback when dictation starts and stops. This is especially helpful when the button's visual change is subtle.
- **Don't:** Don't use the dictation button outside a chat composer context. It's designed for the composer's send-action layout, not as a standalone recording control.
- **Don't:** Don't forget to handle the unsupported case. The button hides itself by default when the browser lacks SpeechRecognition, but you should still design the composer to work without it.

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `dictation` | `UseSpeechRecognitionReturn` | - | The return value from useChatDictation or useSpeechRecognition. Controls all button state: listening, volume, bands, and toggle. **(required)** |
| `size` | `'sm' \| 'md'` | `'md'` | Button size. Matches ChatComposer density. |
| `isHiddenWhenUnsupported` | `boolean` | `true` | When true, renders nothing if the browser does not support SpeechRecognition. When false, keeps the button visible but disabled. |
| `label` | `string` | - | Accessible label override. Defaults to "Start dictation" or "Stop dictation" based on state. |
| `xstyle` | `StyleXStyles` | - | StyleX styles for layout customization (margins, positioning, sizing). Must be a stylex.create() value, not an inline style object like style={{}}. |

