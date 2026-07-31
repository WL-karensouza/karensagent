<!-- PROTOTYPE — 原型变体切换浮动条，验证完即删；生产构建中不渲染 -->
<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

/* 生产构建不渲染切换条，防止原型误上线 */
const isProd = import.meta.env.PROD

const props = defineProps({
  variants: { type: Array, required: true }, // [{ key: 'A', name: '卡片模块式' }, ...]
})

const route = useRoute()
const router = useRouter()

const current = computed(() => route.query.variant || props.variants[0].key)
const currentMeta = computed(
  () => props.variants.find(v => v.key === current.value) || props.variants[0]
)

/* 循环切换变体，写回 URL query（可分享、刷新稳定） */
function cycle(step) {
  const idx = props.variants.findIndex(v => v.key === current.value)
  const next = props.variants[(idx + step + props.variants.length) % props.variants.length]
  router.replace({ query: { ...route.query, variant: next.key } })
}

/* 键盘 ←→ 切换；输入框聚焦时不拦截 */
function onKeydown(e) {
  if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return
  const t = e.target
  if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return
  cycle(e.key === 'ArrowLeft' ? -1 : 1)
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <div v-if="!isProd" class="proto-switcher">
    <button class="proto-arrow" aria-label="上一个变体" @click="cycle(-1)">←</button>
    <span class="proto-label">{{ currentMeta.key }} — {{ currentMeta.name }}</span>
    <button class="proto-arrow" aria-label="下一个变体" @click="cycle(1)">→</button>
  </div>
</template>

<style scoped>
/* 高对比深色药丸：刻意与页面设计区分，一眼可知不是被评设计的一部分 */
.proto-switcher {
  position: fixed;
  left: 50%;
  bottom: 24px;
  transform: translateX(-50%);
  z-index: 999;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 8px;
  background: #2D2A26;
  color: #FDFBF7;
  border-radius: 999px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
  font-size: 0.78rem;
  user-select: none;
}
.proto-arrow {
  width: 30px;
  height: 30px;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: inherit;
  font-size: 1rem;
  font-family: inherit;
  cursor: pointer;
  transition: background 0.15s ease;
}
.proto-arrow:hover { background: rgba(253, 251, 247, 0.15); }
.proto-label {
  padding: 0 10px;
  white-space: nowrap;
  letter-spacing: 0.02em;
}
</style>
