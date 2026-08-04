<!-- AI 问答步骤卡片：展示 karens 实时查数的工具调用过程（友好名 + 状态图标） -->
<template>
  <div class="ai-steps">
    <div v-for="s in steps" :key="s.id" class="step" :class="`is-${s.status}`">
      <span class="step-icon" aria-hidden="true">{{ iconOf(s.status) }}</span>
      <span class="step-label">{{ s.label }}</span>
    </div>
  </div>
</template>

<script setup>
/* 步骤卡片：status = pending | running | done | error */
defineProps({
  steps: { type: Array, default: () => [] },
})
function iconOf(status) {
  if (status === 'done') return '✓'
  if (status === 'error') return '✕'
  if (status === 'running') return '◐'
  return '○'
}
</script>

<style scoped>
/* 步骤卡片容器：浅色卡片，内部步骤纵向排列 */
.ai-steps {
  display: flex; flex-direction: column; gap: 6px;
  background: var(--sent-bg); border: 1px solid var(--border-color);
  border-radius: var(--radius-md); padding: 10px 12px;
}
.step { display: flex; align-items: center; gap: 8px; font-size: 0.76rem; color: var(--sent-mid); }
.step-icon { width: 14px; text-align: center; }
.step.is-done .step-icon { color: var(--success, #2e7d32); }
.step.is-error .step-icon { color: var(--red, #c62828); }
.step.is-running .step-icon { animation: step-spin 1.2s linear infinite; color: var(--accent); }
@keyframes step-spin { to { transform: rotate(360deg); } }
</style>
