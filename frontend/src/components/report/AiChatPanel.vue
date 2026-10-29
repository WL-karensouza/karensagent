<!-- AI 问答助理面板：满高聊天结构，承载真实会话（历史 + 流式回答 + 步骤卡片） -->
<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useStockStore } from '../../stores/stock.js'
import ThinkingStepsCard from './ThinkingStepsCard.vue'
import ChatMessageItem from './ChatMessageItem.vue'
import ChatComposer from './ChatComposer.vue'

const store = useStockStore()
const input = ref('')
const bodyRef = ref(null)

const report = computed(() => store.currentReport)
const stockCode = computed(() => report.value?.stock_code || '')
const stockName = computed(() => report.value?.stock_name || '')

/* 会话归属守卫：store 的 chatMessages 是全局单份，切股票时必须丢弃上一只股票的内容，
   否则会按旧历史误展开。loadedFor 记录「当前展示的消息属于哪只股票」。 */
const loadedFor = ref(null)
/* 请求序号：快速切换股票时，先发的请求若晚返回，不得覆盖后发请求的展示状态 */
let loadSeq = 0

watch(stockCode, async (code) => {
  const my = ++loadSeq
  loadedFor.value = null            // 立刻失效：切股票瞬间不渲染旧消息
  if (!code) return
  try {
    await store.fetchChatSession(code)
  } catch {
    return                          // fetchChatSession 抛错：保持收拢（真实实现内部已吞错，此处为防御）
  }
  if (my !== loadSeq) return        // 期间已切到别的股票，丢弃这次结果
  /* 只认「历史消息条数 > 0」；后端每次都会建会话，不能看 session 是否存在。
     接口失败时 store 不覆盖旧值，下面的归属比对会把面板收回收拢态。 */
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

function send() {
  const q = input.value.trim()
  if (!q || store.chatAsking) return
  /* 清空由 ChatComposer 内部完成（emit('send') 之后自行清空并同步 modelValue），此处不重复清 */
  store.askChat(stockCode.value, {
    question: q,
    report_id: report.value?.id || null,
    stock_name: stockName.value,
  })
  /* askChat 会同步把用户消息推入 chatMessages，此处必须同时把展示权交给当前股票：
     否则 loadedFor 仍为 null，messages 恒为空，面板停在收拢态，用户看不到自己刚发出的提问 */
  loadedFor.value = stockCode.value
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
    <!-- 收拢态：大标题问候 + 舒展档输入容器（整组垂直居中后向下偏移） -->
    <template v-if="!isExpanded">
      <div class="ai-hero">
        <p class="ai-hero-hi"><span aria-hidden="true">✨</span> Hi, Karens</p>
        <h2 class="ai-hero-title">关于这支股票有什么可以帮你的吗？</h2>
      </div>
      <ChatComposer
        v-model="input"
        density="landing"
        :max-rows="5"
        :disabled="store.chatAsking"
        @send="send"
      />
    </template>

    <!-- 展开态：会话区（可滚）+ 紧凑档输入容器（钉底） -->
    <template v-else>
      <div ref="bodyRef" class="ai-body">
        <!-- 消息气泡：单条消息组件（头像 + 元信息行 + 气泡 + 步骤卡片） -->
        <ChatMessageItem v-for="(m, i) in messages" :key="i" :message="m" />

        <!-- 思考过程面板（三行：理解/工具/生成），首个 delta 时 chatSteps 清空即卸载 -->
        <ThinkingStepsCard v-if="steps.length" :steps="steps" />
      </div>
      <ChatComposer
        v-model="input"
        density="compact"
        :max-rows="3"
        :disabled="store.chatAsking"
        @send="send"
      />
    </template>
  </aside>
</template>

<style scoped>
/* 面板：宽度固定 540px（由父容器控制），两态共用同一高度，只切内容 */
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
  /* 193 = 面板自然顶部距 topnav 的偏移 169（主内容 padding 40 + 页面 padding 32 + 返回按钮 37 + 标题 60）+ 底部留白 24，保证首屏完整可见 */
  height: calc(100vh - var(--topnav-height, 64px) - 193px);
  /* min-height 不得超过可用高度，否则矮视口（<677px）下面板会溢出视口导致输入框被裁切 */
  min-height: min(420px, calc(100vh - var(--topnav-height, 64px) - 193px));
}
/* 收拢态：标题与输入容器作为一组居中，再整体下移，视觉重心偏下 */
.ai-panel.is-collapsed { justify-content: center; }
.ai-panel.is-collapsed > * { transform: translateY(20px); }
/* 展开态：消息区撑满，输入容器钉底 */
.ai-panel.is-expanded { justify-content: flex-start; }
/* 会话区占满中间，溢出内部滚动 */
.ai-body {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
/* 收拢态大标题组：小字问候 + 大字主标题 */
.ai-hero { display: flex; flex-direction: column; gap: 6px; }
.ai-hero-hi {
  margin: 0;
  font-size: var(--ax-text-hi);
  color: var(--ax-text-secondary);
  display: flex;
  align-items: center;
  gap: 6px;
}
.ai-hero-title {
  margin: 0;
  font-size: var(--ax-text-display);
  line-height: 1.26;
  font-weight: 400;
  color: var(--ax-text);
}
/* 输入区样式已下沉到 ChatComposer 组件 */
</style>
