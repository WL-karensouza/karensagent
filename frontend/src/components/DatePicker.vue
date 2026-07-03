<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  dates: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:modelValue'])

const isOpen = ref(false)
const pickerRef = ref(null)

/* ── 计算属性 ── */

/* 今天日期字符串 */
const todayStr = computed(() => {
  const d = new Date()
  return d.getFullYear() + '-' +
    String(d.getMonth() + 1).padStart(2, '0') + '-' +
    String(d.getDate()).padStart(2, '0')
})

/* 昨天 */
const yesterdayStr = computed(() => {
  const d = new Date()
  d.setDate(d.getDate() - 1)
  return d.getFullYear() + '-' +
    String(d.getMonth() + 1).padStart(2, '0') + '-' +
    String(d.getDate()).padStart(2, '0')
})

/* 日期标签 */
function dateLabel(d) {
  if (d === todayStr.value) return '今天'
  if (d === yesterdayStr.value) return '昨天'
  return ''
}

/* ── 交互 ── */

function toggle() {
  isOpen.value = !isOpen.value
}

function select(d) {
  emit('update:modelValue', d)
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
  <div ref="pickerRef" class="datepicker">
    <!-- 触发按钮 -->
    <button type="button" class="datepicker-trigger" :class="{ open: isOpen }" @click="toggle">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
        <line x1="16" y1="2" x2="16" y2="6"/>
        <line x1="8" y1="2" x2="8" y2="6"/>
        <line x1="3" y1="10" x2="21" y2="10"/>
      </svg>
      <span class="datepicker-value">{{ modelValue }}</span>
      <svg class="datepicker-chevron" width="12" height="12" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
        <polyline points="6 9 12 15 18 9"/>
      </svg>
    </button>

    <!-- 下拉列表 -->
    <transition name="dp-fade">
      <div v-if="isOpen" class="datepicker-dropdown">
        <div class="datepicker-list">
          <button
            v-for="d in dates"
            :key="d"
            type="button"
            class="datepicker-item"
            :class="{
              active: d === modelValue,
              today: d === todayStr,
            }"
            @click="select(d)"
          >
            <span class="dp-date">{{ d }}</span>
            <span v-if="dateLabel(d)" class="dp-label">{{ dateLabel(d) }}</span>
            <svg v-if="d === modelValue" class="dp-check" width="16" height="16"
              viewBox="0 0 24 24" fill="none" stroke="currentColor"
              stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
          </button>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
/* ── 容器 ── */
.datepicker {
  position: relative;
  min-width: 200px;
}

/* ── 触发按钮 ── */
.datepicker-trigger {
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
.datepicker-trigger:hover {
  border-color: var(--accent);
}
.datepicker-trigger.open {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-light);
}
.datepicker-chevron {
  margin-left: auto;
  color: var(--text-muted);
  transition: transform 0.2s ease;
}
.datepicker-trigger.open .datepicker-chevron {
  transform: rotate(180deg);
}

/* ── 下拉浮层 ── */
.datepicker-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 0; right: 0;
  min-width: 220px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-hover);
  z-index: 200;
  overflow: hidden;
}

/* ── 列表 ── */
.datepicker-list {
  max-height: 252px;
  overflow-y: auto;
  padding: 4px;
}

/* ── 列表项 ── */
.datepicker-item {
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
.datepicker-item:hover {
  background: var(--bg-hover);
}
.datepicker-item.active {
  color: var(--accent);
  font-weight: 600;
  background: var(--accent-light);
}

/* ── 标签 ── */
.dp-label {
  font-size: 0.78rem;
  color: var(--text-muted);
  font-weight: 400;
}
.datepicker-item.active .dp-label {
  color: var(--accent);
  opacity: 0.7;
}

/* ── 勾号 ── */
.dp-check {
  margin-left: auto;
  color: var(--accent);
}

/* ── 动画 ── */
.dp-fade-enter-active { transition: opacity 0.15s ease, transform 0.15s ease; }
.dp-fade-leave-active { transition: opacity 0.1s ease, transform 0.1s ease; }
.dp-fade-enter-from { opacity: 0; transform: translateY(-4px); }
.dp-fade-leave-to   { opacity: 0; transform: translateY(-2px); }
</style>
