astryx: answered by CLI 0.7.4 with Core 0.7.4, outside a project
package: @astryxdesign/core

# ChatComposerInput

Pass ChatComposerInput to ChatComposer's input slot when the draft needs trigger menus, inline tokens, history recall, dictation insertion, or file intake.

**Import:** `import {ChatComposerInput} from '@astryxdesign/core/Chat';`

## Anatomy

| Element | Required | Description |
|---------|----------|-------------|
| Input root | Yes | The themed container that forwards the root ref and BaseProps styling seams. |
| Editable surface | Yes | The labeled contenteditable textbox or combobox that owns text, selection, keyboard, paste, and drop behavior. |
| Placeholder | No | Visual guidance shown only while the serialized draft is empty. |
| Trigger menu | No | The suggestion popup rendered while a configured trigger is active. |
| Inline token | No | A non-editable badge or custom rendering with a stable serialized value. |

## Best Practices

- **Do:** Use handleRef for programmatic text or token insertion; inserted text follows the same onChange pipeline as typing.
- **Do:** Use onFiles for files pasted or dropped onto the editor, and keep file validation and upload progress in the product layer.
- **Don't:** Use custom token rendering for ordinary mentions or commands; prefer the structured badge form so tokens remain predictable and themeable.

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `handleRef` | `React.Ref<ChatComposerInputHandle>` | - | Imperative handle for programmatic control: insertToken, expandToken, insertText, focus, and getValue. |
| `value` | `string` | - | Controlled input value. Pair with onChange for two-way binding. |
| `onChange` | `(value: string) => void` | - | Called when the input value changes. The serialized string includes token placeholders. |
| `placeholder` | `string` | `'Type a message...'` | Placeholder text shown when the input is empty. |
| `maxRows` | `number` | `8` | Maximum visible rows before the input scrolls. Use a lower value in compact layouts. |
| `triggers` | `ChatComposerTrigger[]` | - | Trigger definitions for typeahead menus. Each trigger specifies a character (@ or /), a search source, and an onSelect handler that returns the token to insert. Set hasMultiWordQuery: true when suggestions contain spaces (people, topics): the query then runs to a line break or about 64 characters instead of ending at the first space. Per-trigger emptySearchText (ReactNode) is the message when the query matched nothing. |
| `debounceMs` | `number` | `150` | Debounce delay for async search sources to avoid excessive network requests. |
| `hasHistory` | `boolean` | `true` | Enable ArrowUp/Down to recall previously submitted messages. |
| `label` | `string` | `'Message input'` | Accessible label announced by screen readers. |
| `isDisabled` | `boolean` | `false` | Disables the input. Use during streaming or when a prerequisite is unmet. |
| `onPaste` | `(event, text) => boolean \| void` | - | Called when plain text is pasted. Return true after handling the text yourself; otherwise ChatComposerInput inserts it or applies paste-as-token behavior. |
| `pasteAsToken` | `UseChatPasteAsTokenReturn \| false` | - | Paste-as-token behavior. By default, plain-text pastes over 200 characters become expandable tokens. Pass false to keep every text paste inline, or provide useChatPasteAsToken() to customize the conversion. |
| `onFiles` | `(files: File[]) => void` | - | Called when files are pasted or dropped onto the input. Use to handle attachments. |
| `onSubmit` | `(value: string) => void` | - | Called when the user presses Enter without Shift. The serialized value includes token placeholders. |
| `onKeyDown` | `(event) => void` | - | Key-down handler invoked before the built-in Enter/history behavior (after any open trigger menu). The seam for platform-specific keys: call event.preventDefault() to suppress the default submit (e.g. newline on a touch keyboard), or act on the event yourself to add behavior (e.g. submit on Cmd/Ctrl+Enter). IME composition is always respected; Enter never submits mid-composition. |

