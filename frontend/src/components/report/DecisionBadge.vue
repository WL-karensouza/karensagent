<!-- 多空判断徽章：中性底 + 边框，方向由符号颜色承担（去 emoji 与彩色底） -->
<script setup>
import { verdictColor, verdictSym } from '../../utils/stock.js'

defineProps({
  decision: { type: String, required: true },
})
</script>

<template>
  <span v-if="decision" class="decision-badge">
    <span class="dec-sym" :style="{ color: verdictColor(decision) }">{{ verdictSym(decision) }}</span>
    {{ decision }}
  </span>
</template>

<style scoped>
/* 决策徽章：中性底 + 边框，方向由符号颜色承担 */
.decision-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 14px;
  border-radius: 999px;
  background: var(--sent-bg);
  border: 1px solid var(--border-color);
  color: var(--sent-strong);
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}
.dec-sym { font-weight: 700; }
</style>
