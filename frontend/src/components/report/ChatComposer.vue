<!-- 问答输入容器：浅灰托盘内嵌白色输入框，含装饰工具行与圆形发送键（astryx landing 形态） -->
<script setup>
import { ref, computed, watch, nextTick } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  /* landing = 收拢态舒展档；compact = 展开态紧凑档 */
  density: { type: String, default: 'landing' },
  maxRows: { type: Number, default: 5 },
  disabled: { type: Boolean, default: false },
  placeholder: { type: String, default: '输入问题，Enter 发送' },
})

const emit = defineEmits(['update:modelValue', 'send'])

/* 行高与 textarea 高度计算保持一致（见样式里 line-height: 22px） */
const LINE_HEIGHT = 22

const text = ref(props.modelValue)
const taRef = ref(null)

/* 外部改值（如发送后清空、切换股票重置）同步进内部状态 */
watch(() => props.modelValue, (v) => { text.value = v })

/* 空输入或禁用时不可发送 */
const canSend = computed(() => !props.disabled && text.value.trim().length > 0)

function syncHeight() {
  const ta = taRef.value
  if (!ta) return
  ta.style.height = 'auto'
  const max = props.maxRows * LINE_HEIGHT
  ta.style.height = Math.min(ta.scrollHeight, max) + 'px'
}

function onInput(e) {
  text.value = e.target.value
  emit('update:modelValue', text.value)
  syncHeight()
}

function doSend() {
  if (!canSend.value) return
  emit('send')
  text.value = ''
  emit('update:modelValue', '')
  /* 发送后高度复位到单行/最小高度 */
  nextTick(() => {
    const ta = taRef.value
    if (ta) ta.style.height = ''
  })
}

/* Enter 发送 / Shift+Enter 换行；中文输入法选词回车（isComposing / 229）必须放行 */
function onKeydown(e) {
  if (e.key !== 'Enter') return
  if (e.shiftKey) return
  if (e.isComposing || e.keyCode === 229) return
  e.preventDefault()
  doSend()
}

defineExpose({ focus: () => taRef.value?.focus() })
</script>

<template>
  <div class="composer-tray" :class="`is-${density}`">
    <div class="composer-inner">
      <textarea
        ref="taRef"
        class="composer-textarea"
        :value="text"
        :placeholder="placeholder"
        :disabled="disabled"
        rows="1"
        @input="onInput"
        @keydown="onKeydown"
      ></textarea>
      <div class="composer-tools">
        <button
          class="composer-send"
          type="button"
          :disabled="!canSend"
          aria-label="发送"
          @click="doSend"
        >↑</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 外层托盘：浅灰底 + 大圆角 + 悬浮阴影，聚焦时阴影加深 */
.composer-tray {
  background: var(--ax-hover);
  border-radius: var(--ax-radius-tray);
  padding: var(--ax-pad-tray);
  box-shadow: var(--ax-shadow-low);
  transition: box-shadow 0.15s ease;
}
.composer-tray:focus-within { box-shadow: var(--ax-shadow-med); }
.composer-tray.is-compact { padding: var(--ax-pad-tray-compact); }

/* 内层白框：承载输入与工具行 */
.composer-inner {
  background: var(--ax-surface);
  border-radius: var(--ax-radius-inner);
  padding: 9px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.composer-tray.is-compact .composer-inner { padding: 6px 10px; gap: 4px; }

/* 输入区：无边框无轮廓，高度由脚本按内容与 maxRows 计算 */
.composer-textarea {
  border: none;
  outline: none;
  resize: none;
  background: transparent;
  font-family: inherit;
  font-size: 0.82rem;
  line-height: 22px;
  color: var(--ax-text);
  overflow-y: auto;
  padding: 0;
  display: block;
  width: 100%;
  box-sizing: border-box;
}
.composer-textarea::placeholder { color: var(--ax-text-secondary); }
.composer-tray.is-landing .composer-textarea { min-height: 63px; }
.composer-tray.is-compact .composer-textarea { min-height: 22px; }

/* 底行：仅保留圆形发送键，右对齐 */
.composer-tools { display: flex; align-items: center; justify-content: flex-end; }
.composer-send {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  border: none;
  background: var(--ax-accent);
  color: #fff;
  font-size: 0.9rem;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: opacity 0.15s ease;
}
.composer-send:disabled { opacity: 0.45; cursor: not-allowed; }
</style>
