<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  options: { type: Array, default: () => [] },
  /* [{ label: '周榜', value: 'weekly' }, ...] */
})

const emit = defineEmits(['update:modelValue'])

const isOpen = ref(false)
const pickerRef = ref(null)

const selectedLabel = ref('')

/* 同步默认值标签 */
watch(() => props.modelValue, (val) => {
  const found = props.options.find(o => o.value === val)
  selectedLabel.value = found ? found.label : val
}, { immediate: true })

function toggle() {
  isOpen.value = !isOpen.value
}

function select(opt) {
  selectedLabel.value = opt.label
  emit('update:modelValue', opt.value)
  isOpen.value = false
}

/* 点击外部关闭 */
function handleClickOutside(e) {
  if (pickerRef.value && !pickerRef.value.contains(e.target)) {
    isOpen.value = false
  }
}

watch(isOpen, (val) => {
  if (val) {
    document.addEventListener('click', handleClickOutside)
  } else {
    document.removeEventListener('click', handleClickOutside)
  }
})
</script>

<template>
  <div ref="pickerRef" class="selectpicker">
    <!-- 触发按钮 -->
    <button type="button" class="picker-trigger" :class="{ open: isOpen }" @click="toggle">
      <span class="picker-value">{{ selectedLabel }}</span>
      <svg class="picker-chevron" width="12" height="12" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
        <polyline points="6 9 12 15 18 9"/>
      </svg>
    </button>

    <!-- 下拉列表 -->
    <transition name="sp-fade">
      <div v-if="isOpen" class="picker-dropdown">
        <button
          v-for="opt in options"
          :key="opt.value"
          type="button"
          class="picker-item"
          :class="{ active: opt.value === modelValue }"
          @click="select(opt)"
        >
          <span>{{ opt.label }}</span>
          <svg v-if="opt.value === modelValue" class="sp-check" width="16" height="16"
            viewBox="0 0 24 24" fill="none" stroke="currentColor"
            stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
        </button>
      </div>
    </transition>
  </div>
</template>

<style scoped>
/* ── 容器 ── */
.selectpicker {
  position: relative;
  min-width: 160px;
}

/* ── 触发按钮 ── */
.picker-trigger {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 14px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  color: var(--text-primary);
  font-size: 0.9rem;
  font-family: inherit;
  cursor: pointer;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.picker-trigger:hover {
  border-color: var(--accent);
}
.picker-trigger.open {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-light);
}
.picker-chevron {
  margin-left: auto;
  color: var(--text-muted);
  transition: transform 0.2s ease;
}
.picker-trigger.open .picker-chevron {
  transform: rotate(180deg);
}

/* ── 下拉浮层 ── */
.picker-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 0; right: 0;
  min-width: 160px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-hover);
  z-index: 200;
  overflow: hidden;
  padding: 4px;
}

/* ── 列表项 ── */
.picker-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 9px 12px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--text-primary);
  font-size: 0.9rem;
  font-family: inherit;
  cursor: pointer;
  transition: background 0.12s ease;
  text-align: left;
}
.picker-item:hover {
  background: var(--bg-hover);
}
.picker-item.active {
  color: var(--accent);
  font-weight: 600;
  background: var(--accent-light);
}

/* ── 勾号 ── */
.sp-check {
  margin-left: auto;
  color: var(--accent);
}

/* ── 动画 ── */
.sp-fade-enter-active { transition: opacity 0.15s ease, transform 0.15s ease; }
.sp-fade-leave-active { transition: opacity 0.1s ease, transform 0.1s ease; }
.sp-fade-enter-from { opacity: 0; transform: translateY(-4px); }
.sp-fade-leave-to   { opacity: 0; transform: translateY(-2px); }
</style>
