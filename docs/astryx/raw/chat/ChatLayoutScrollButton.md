astryx: answered by CLI 0.7.4 with Core 0.7.4, outside a project
package: @astryxdesign/core

# ChatLayoutScrollButton

Floating scroll-to-bottom button that appears when the user scrolls away from the latest messages. It fades in as a compact icon button and expands to show a label when new messages arrive. ChatLayout renders this by default: pass a custom element to the scrollButton prop to override, or null to hide it entirely.

**Import:** `import {ChatLayoutScrollButton} from '@astryxdesign/core/Chat';`

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `isVisible` | `boolean` | - | Whether the button is visible. Bind to a scroll-position check so the button only appears when the user has scrolled up. **(required)** |
| `label` | `string` | - | Optional label that expands the button (e.g. "New messages"). Use to signal unread content below the fold. |
| `onClick` | `() => void` | - | Click handler: typically scrolls to bottom and dismisses the new message indicator. **(required)** |

