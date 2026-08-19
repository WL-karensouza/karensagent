<!-- AI 问答思考过程面板：理解行 / 工具行（动态）/ 生成行，无任何交互元素，最终回答出现时由父组件卸载 -->
<script setup>
defineProps({
  steps: { type: Array, default: () => [] },
})

/* 状态图标：running=◐（旋转）/ done=✓ / error=✕ / 其余 pending=○ */
function iconOf(status) {
  if (status === 'done') return '✓'
  if (status === 'error') return '✕'
  if (status === 'running') return '◐'
  return '○'
}
</script>

<template>
  <div class="thinking-steps">
    <div v-for="(s, i) in steps" :key="i" class="ts-row" :class="`is-${s.status}`">
      <span class="ts-icon">{{ iconOf(s.status) }}</span>
      <span class="ts-label">{{ s.label }}</span>
    </div>
  </div>
</template>

<style scoped>
/* 思考过程面板：浅色卡片，行间紧凑，高度随步骤数自适应；首个 delta 时由父组件卸载 */
.thinking-steps {
  /* 防止会话历史溢出时被 flex 压缩（原默认 flex-shrink:1 会把卡片压成一行高、裁掉其余步骤） */
  flex-shrink: 0;
  display: flex; flex-direction: column; gap: 5px;
  background: var(--sent-bg); border: 1px solid var(--border-color);
  border-radius: var(--radius-md); padding: 8px 12px;
  box-sizing: border-box;
}
/* 行：状态图标 + 文案，浅灰小字 */
.ts-row {
  display: flex; align-items: center; gap: 8px;
  font-size: 0.76rem; color: var(--sent-mid); line-height: 1.5;
}
.ts-icon { width: 14px; text-align: center; flex-shrink: 0; }
/* 进行中：图标旋转；完成：绿色；失败：红色 */
.ts-row.is-running .ts-icon { animation: ts-spin 1.2s linear infinite; color: var(--accent); }
.ts-row.is-done .ts-icon { color: var(--success, #2e7d32); }
.ts-row.is-error .ts-icon { color: var(--red, #c62828); }
@keyframes ts-spin { to { transform: rotate(360deg); } }
</style>
