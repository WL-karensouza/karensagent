<!-- AI 问答助理面板：满高聊天结构，承载真实会话（历史 + 流式回答 + 步骤卡片） -->
<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useStockStore } from '../../stores/stock.js'
import ThinkingStepsCard from './ThinkingStepsCard.vue'
import ChatMessageItem from './ChatMessageItem.vue'

const store = useStockStore()
const input = ref('')
const bodyRef = ref(null)

const report = computed(() => store.currentReport)
const stockCode = computed(() => report.value?.stock_code || '')
const stockName = computed(() => report.value?.stock_name || '')

/* 会话归属守卫：store 的 chatMessages 是全局单份，切股票时必须丢弃上一只股票的内容，
   否则会按旧历史误展开。loadedFor 记录「当前展示的消息属于哪只股票」。 */
const loadedFor = ref(null)

watch(stockCode, async (code) => {
  loadedFor.value = null            // 立刻失效：切股票瞬间不渲染旧消息
  if (!code) return
  try {
    await store.fetchChatSession(code)
  } catch {
    return                          // 接口失败：保持收拢，不阻断页面
  }
  /* 只认「历史消息条数 > 0」；后端每次都会建会话，不能看 session 是否存在 */
  const sameStock = store.chatSession?.stock_code === code
  loadedFor.value = sameStock && store.chatMessages.length > 0 ? code : null
}, { immediate: true })

/* 仅当归属匹配时才把 store 的消息透给模板（单条消息结构下沉到 ChatMessageItem） */
const messages = computed(() =>
  loadedFor.value === stockCode.value ? store.chatMessages : []
)
const steps = computed(() =>
  loadedFor.value === stockCode.value ? store.chatSteps : []
)
/* 有历史消息即展开；收拢态只在无会话时出现 */
const isExpanded = computed(() => messages.value.length > 0)

async function send() {
  const q = input.value.trim()
  if (!q || store.chatAsking) return
  input.value = ''
  store.askChat(stockCode.value, {
    question: q,
    report_id: report.value?.id || null,
    stock_name: stockName.value,
  })
}

/* ── 聊天框自动滚动到底：发送消息 / 思考面板出现 / 流式回答增长时，都滚到最新可见 ── */
function scrollToBottom() {
  if (!bodyRef.value) return
  nextTick(() => {
    bodyRef.value.scrollTop = bodyRef.value.scrollHeight
  })
}
watch(() => store.chatMessages.length, scrollToBottom)
watch(() => store.chatSteps.length, scrollToBottom)
watch(() => store.chatMessages[store.chatMessages.length - 1]?.content, scrollToBottom)
</script>

<template>
  <aside class="ai-panel" :class="isExpanded ? 'is-expanded' : 'is-collapsed'">
    <!-- 头部：karens 标识（固定） -->
    <header class="ai-head">
      <div class="ai-id">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
        </svg>
        <strong>Karens 问答助理</strong>
      </div>
    </header>

    <!-- 会话区：滚动承载消息气泡 + 思考态 + 实时步骤卡片 -->
    <div ref="bodyRef" class="ai-body">
      <!-- 空态：无消息时显示欢迎语 -->
      <div v-if="!messages.length" class="ai-empty">
        <p>对这份投研报告有任何疑问，尽管问 Karens。</p>
      </div>

      <!-- 消息气泡：单条消息组件（头像 + 元信息行 + 气泡 + 步骤卡片） -->
      <ChatMessageItem v-for="(m, i) in messages" :key="i" :message="m" />

      <!-- 思考过程面板（三行：理解/工具/生成），首个 delta 时 chatSteps 清空即卸载 -->
      <ThinkingStepsCard v-if="steps.length" :steps="steps" />
    </div>

    <!-- 输入区（钉底；发送中禁用防重复提交） -->
    <footer class="ai-input">
      <input v-model="input" type="text" placeholder="输入问题，回车发送"
             @keyup.enter="send" :disabled="store.chatAsking" />
      <button type="button" @click="send" :disabled="store.chatAsking || !input.trim()">发送</button>
    </footer>
  </aside>
</template>

<style scoped>
/* 面板：宽度固定 540px（由父容器控制），高度在收拢/展开之间过渡 */
.ai-panel {
  background: var(--ax-surface);
  border: 1px solid var(--ax-neutral);
  border-radius: 20px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-sizing: border-box;
  overflow: hidden;
  transition: height 0.28s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}
.ai-panel:hover {
  border-color: var(--ax-accent);
  box-shadow: 0 4px 16px rgba(10, 19, 23, 0.06);
}
/* 收拢态：无历史会话时只占 240px，问候语与输入框垂直居中 */
.ai-panel.is-collapsed {
  height: 240px;
  justify-content: center;
}
/* 展开态：有历史消息时占满右栏可用高度，消息区内部滚动 */
.ai-panel.is-expanded {
  height: calc(100vh - var(--topnav-height, 64px) - 48px);
  min-height: 520px;
}
/* 会话区占满中间，溢出内部滚动 */
.ai-body {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
/* 头部 */
.ai-head { display: flex; align-items: center; justify-content: space-between; }
.ai-id { display: flex; align-items: center; gap: 8px; color: var(--ax-text); font-size: 0.92rem; }
/* 空态：无历史消息时居中引导 */
.ai-empty {
  margin: auto;
  text-align: center;
  color: var(--ax-text-secondary);
  font-size: 0.82rem;
  line-height: 1.7;
  padding: 0 12px;
}
/* 输入区：钉底，发送键用 astryx 强调蓝 */
.ai-input {
  display: flex; gap: 8px; flex-shrink: 0;
  padding-top: 14px; border-top: 1px solid var(--ax-neutral);
}
.ai-input input {
  flex: 1; min-width: 0; border: 1px solid var(--ax-neutral); border-radius: 12px;
  padding: 9px 12px; font-size: 0.8rem; font-family: inherit;
  color: var(--ax-text); background: var(--ax-surface); outline: none;
  transition: border-color 0.15s ease;
}
.ai-input input:focus { border-color: var(--ax-accent); }
.ai-input input:disabled { color: var(--ax-text-secondary); cursor: not-allowed; }
.ai-input input::placeholder { color: var(--ax-text-secondary); }
.ai-input button {
  height: 36px; padding: 0 16px; border: none; border-radius: 12px;
  background: var(--ax-accent); color: #fff; font-size: 0.78rem; font-family: inherit;
  cursor: pointer; transition: opacity 0.15s ease;
}
.ai-input button:hover:not(:disabled) { opacity: 0.88; }
.ai-input button:disabled { opacity: 0.45; cursor: not-allowed; }
</style>
