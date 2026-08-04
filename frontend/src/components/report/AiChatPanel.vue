<!-- AI 问答助理面板：满高聊天结构，承载真实会话（历史 + 流式回答 + 步骤卡片） -->
<script setup>
import { ref, computed, onMounted } from 'vue'
import { marked } from 'marked'
import { useStockStore } from '../../stores/stock.js'
import AiStepsCard from './AiStepsCard.vue'

const store = useStockStore()
const input = ref('')

const report = computed(() => store.currentReport)
const stockCode = computed(() => report.value?.stock_code || '')
const stockName = computed(() => report.value?.stock_name || '')

/* 历史消息渲染（含 tool_calls 转步骤卡片） */
const messages = computed(() => store.chatMessages)
const thinking = computed(() => store.chatThinking)
const toolSteps = computed(() => store.chatToolSteps)
function renderMd(text) { return marked.parse(text) }

function toolStepsFromRecord(record) {
  return (record.tool_calls || []).map((tc, i) => ({
    id: i, label: tc.label || tc.name, status: tc.ok ? 'done' : 'error',
  }))
}

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

onMounted(() => {
  if (stockCode.value) store.fetchChatSession(stockCode.value)
})
</script>

<template>
  <aside class="ai-panel">
    <!-- 头部：karens 标识（固定） -->
    <header class="ai-head">
      <div class="ai-id">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
        </svg>
        <strong>karens 问答助理</strong>
      </div>
    </header>

    <!-- 会话区：滚动承载消息气泡 + 思考态 + 实时步骤卡片 -->
    <div class="ai-body">
      <!-- 空态：无消息时显示欢迎语 -->
      <div v-if="!messages.length" class="ai-empty">
        <p>对这份投研报告有任何疑问，尽管问 karens。</p>
      </div>

      <!-- 消息气泡 -->
      <div v-for="(m, i) in messages" :key="i" class="msg" :class="m.role">
        <div class="bubble" v-html="renderMd(m.content)"></div>
        <AiStepsCard v-if="m.role === 'assistant' && m.tool_calls" :steps="toolStepsFromRecord(m)" />
      </div>

      <!-- 思考中 -->
      <div v-if="thinking" class="ai-thinking">
        <span class="ai-dots"><i></i><i></i><i></i></span>
        <span>karens 正在理解你的问题…</span>
      </div>

      <!-- 工具步骤卡片（实时） -->
      <AiStepsCard v-if="toolSteps.length" :steps="toolSteps" />
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
/* 满高聊天面板：顶栏 + 会话区(可滚) + 钉底输入，外形不随内容跳动 */
.ai-panel {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: calc(100vh - var(--topnav-height, 64px) - 48px);
  min-height: 520px;
  box-sizing: border-box;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.ai-panel:hover {
  border-color: var(--sent-soft);
  box-shadow: 0 4px 16px rgba(45, 42, 38, 0.06);
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
.ai-id { display: flex; align-items: center; gap: 8px; color: var(--sent-strong); font-size: 0.92rem; }
/* 空态：无历史消息时居中引导 */
.ai-empty {
  margin: auto;
  text-align: center;
  color: var(--sent-mid);
  font-size: 0.82rem;
  line-height: 1.7;
  padding: 0 12px;
}
/* 消息行：用户右对齐 / 助理左对齐 */
.msg { display: flex; flex-direction: column; gap: 6px; }
.msg.user { align-items: flex-end; }
.msg.assistant { align-items: flex-start; }
/* 气泡：浅色系，最大宽避免顶满 */
.bubble {
  max-width: 92%;
  padding: 9px 12px;
  border-radius: var(--radius-md);
  font-size: 0.82rem;
  line-height: 1.65;
  word-break: break-word;
}
.bubble :deep(p) { margin: 0 0 6px; }
.bubble :deep(p:last-child) { margin-bottom: 0; }
.bubble :deep(ul), .bubble :deep(ol) { margin: 4px 0; padding-left: 18px; }
.bubble :deep(strong) { font-weight: 600; }
.bubble :deep(code) { background: var(--bg-hover); padding: 1px 5px; border-radius: 4px; font-size: 0.78rem; }
.msg.user .bubble {
  background: var(--accent);
  color: #fff;
  border-bottom-right-radius: 4px;
}
.msg.assistant .bubble {
  background: var(--sent-bg);
  color: var(--sent-strong);
  border-bottom-left-radius: 4px;
}
/* 思考中提示：浅色 + 呼吸三点 */
.ai-thinking {
  display: flex; align-items: center; gap: 8px;
  font-size: 0.76rem; color: var(--sent-mid);
}
.ai-dots { display: flex; gap: 6px; }
.ai-dots i {
  width: 5px; height: 5px; border-radius: 50%; background: var(--sent-soft);
  animation: ai-breathe 1.8s ease-in-out infinite;
}
.ai-dots i:nth-child(2) { animation-delay: 0.3s; }
.ai-dots i:nth-child(3) { animation-delay: 0.6s; }
@keyframes ai-breathe {
  0%, 100% { opacity: 0.3; transform: scale(0.85); }
  50% { opacity: 1; transform: scale(1); }
}
/* 输入区钉底 */
.ai-input {
  display: flex; gap: 8px; flex-shrink: 0;
  padding-top: 14px; border-top: 1px solid var(--border-color);
}
.ai-input input {
  flex: 1; min-width: 0; border: 1px solid var(--border-color); border-radius: var(--radius-md);
  padding: 9px 12px; font-size: 0.8rem; font-family: inherit; color: var(--sent-strong);
  background: var(--bg-subtle); outline: none;
  transition: border-color 0.15s ease;
}
.ai-input input:focus { border-color: var(--accent); }
.ai-input input:disabled { color: var(--sent-soft); cursor: not-allowed; }
.ai-input input::placeholder { color: var(--sent-soft); }
.ai-input button {
  height: 36px; padding: 0 16px; border: none; border-radius: var(--radius-md);
  background: var(--accent); color: #fff; font-size: 0.78rem; font-family: inherit;
  cursor: pointer; transition: background 0.15s ease;
}
.ai-input button:hover:not(:disabled) { background: var(--accent-hover); }
.ai-input button:disabled { opacity: 0.45; cursor: not-allowed; }
</style>
