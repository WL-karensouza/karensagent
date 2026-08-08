<script setup>
/* ═══════════════════════════════════════════
   CharacterBubble —— 人物头顶对话气泡
   输入目标世界坐标，渲染循环投影到屏幕定位 div
   show(text) 显示台词，DURATION 秒后自动淡出
   ═══════════════════════════════════════════ */
import { ref, onMounted, onUnmounted } from 'vue'
import { useTres, useLoop } from '@tresjs/core'
import { Vector3 } from 'three'

const props = defineProps({
  target: { type: Object, default: () => ({ x: 0, y: 2, z: 0 }) }, // 世界坐标（头顶上方）
})

const DURATION = 3000
const visible = ref(false)
const text = ref('')
const style = ref({ left: '50%', top: '50%' })
let hideTimer = null
let worldPos = new Vector3(props.target.x, props.target.y, props.target.z)

const { camera } = useTres()
const { onRender } = useLoop()

onRender(() => {
  if (!visible.value) return
  const cam = camera.value?.__tres?.object ?? camera.value
  if (!cam) return
  // 世界→屏幕投影
  const v = worldPos.clone().project(cam)
  if (v.z < 1) {
    style.value = {
      left: `${(v.x * 0.5 + 0.5) * 100}%`,
      top: `${(-v.y * 0.5 + 0.5) * 100}%`,
    }
  }
})

function show(msg) {
  text.value = msg
  visible.value = true
  clearTimeout(hideTimer)
  hideTimer = setTimeout(() => { visible.value = false }, DURATION)
}

defineExpose({ show })

onUnmounted(() => clearTimeout(hideTimer))
</script>

<template>
  <div class="character-bubble-layer">
    <transition name="bubble">
      <div v-if="visible" class="character-bubble" :style="style">
        {{ text }}
        <span class="bubble-arrow" />
      </div>
    </transition>
  </div>
</template>

<style scoped>
/* ══ 对话气泡浮层 ══
   绝对定位覆盖场景；气泡投影定位；白底圆角+箭头+浅色描边 */
.character-bubble-layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
}
.character-bubble {
  position: absolute;
  transform: translate(-50%, -100%);
  padding: 6px 14px;
  background: rgba(255, 255, 255, 0.95);
  color: var(--text-secondary, #444);
  font-size: 0.85rem;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.12);
  border: 1px solid rgba(0, 0, 0, 0.06);
}
.bubble-arrow {
  position: absolute;
  left: 50%;
  bottom: -6px;
  transform: translateX(-50%);
  width: 12px;
  height: 12px;
  background: inherit;
  border-right: 1px solid rgba(0, 0, 0, 0.06);
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  transform: translateX(-50%) rotate(45deg);
}
.bubble-enter-active, .bubble-leave-active { transition: opacity 0.2s ease; }
.bubble-enter-from, .bubble-leave-to { opacity: 0; }
</style>
