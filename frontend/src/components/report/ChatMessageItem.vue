<!-- 单条聊天消息：头像 + 元信息行（名称·时间）+ 气泡，微信式镜像布局 -->
<script setup>
import { computed } from 'vue'
import { marked } from 'marked'
import assistantAvatar from '../../assets/chat/assistant.svg'
import userAvatar from '../../assets/chat/user.svg'
import { formatChatTime } from '../../utils/time.js'

const props = defineProps({
  message: { type: Object, required: true },
})

/* 对话双方固定显示名称 */
const USER_NAME = 'Simon'
const ASSISTANT_NAME = 'Karens'

const isUser = computed(() => props.message.role === 'user')
/* 元信息行：双方都显示「名称 · 时间」 */
const metaText = computed(() => {
  const t = formatChatTime(props.message.created_at)
  return [isUser.value ? USER_NAME : ASSISTANT_NAME, t].filter(Boolean).join(' · ')
})

function renderMd(text) { return marked.parse(text) }
</script>

<template>
  <div class="chat-msg" :class="message.role">
    <img class="chat-avatar" :src="isUser ? userAvatar : assistantAvatar"
         :alt="isUser ? '用户头像' : '助理头像'" />
    <div class="chat-main">
      <!-- 元信息行：助理在头像右上方、用户镜像在左上方；无时间且非助理时整行不渲染 -->
      <div v-if="metaText" class="chat-meta">{{ metaText }}</div>
      <div class="chat-bubble" v-html="renderMd(message.content)"></div>
    </div>
  </div>
</template>

<style scoped>
/* 消息行：助理左对齐 / 用户右对齐镜像 */
.chat-msg { display: flex; gap: 8px; }
.chat-msg.user { flex-direction: row-reverse; }
/* 圆形头像，固定尺寸不随内容缩放 */
.chat-avatar { width: 34px; height: 34px; border-radius: 50%; flex-shrink: 0; }
/* 主列：元信息行 + 气泡 + 步骤卡片，用户侧右对齐 */
.chat-main {
  display: flex; flex-direction: column; gap: 4px;
  align-items: flex-start; min-width: 0; max-width: calc(100% - 42px);
}
.chat-msg.user .chat-main { align-items: flex-end; }
/* 元信息行：名称·时间，浅灰小字 */
.chat-meta { font-size: 0.72rem; color: var(--sent-mid); line-height: 1.4; }
/* 气泡：浅色系，最大宽避免顶满 */
.chat-bubble {
  max-width: 100%;
  padding: 9px 12px;
  border-radius: var(--radius-md);
  font-size: 0.82rem;
  line-height: 1.65;
  word-break: break-word;
  box-sizing: border-box;
}
.chat-bubble :deep(p) { margin: 0 0 6px; }
.chat-bubble :deep(p:last-child) { margin-bottom: 0; }
.chat-bubble :deep(ul), .chat-bubble :deep(ol) { margin: 4px 0; padding-left: 18px; }
.chat-bubble :deep(strong) { font-weight: 600; }
.chat-bubble :deep(code) { background: var(--bg-hover); padding: 1px 5px; border-radius: 4px; font-size: 0.78rem; }
.chat-msg.user .chat-bubble {
  background: var(--accent);
  color: #fff;
  border-bottom-right-radius: 4px;
}
.chat-msg.assistant .chat-bubble {
  background: var(--sent-bg);
  color: var(--sent-strong);
  border-bottom-left-radius: 4px;
}
</style>
