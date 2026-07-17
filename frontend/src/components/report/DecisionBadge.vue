<!-- 多空判断徽章（方案4） -->
<script setup>
import { computed } from 'vue'

const props = defineProps({
  decision: { type: String, required: true },
})

const config = computed(() => {
  const map = {
    '看多': { icon: '🟢', class: 'badge-bull', label: '看多' },
    '震荡': { icon: '🟡', class: 'badge-neutral', label: '震荡' },
    '看空': { icon: '🔴', class: 'badge-bear', label: '看空' },
  }
  return map[props.decision] || { icon: '⚪', class: 'badge-neutral', label: props.decision || '未知' }
})
</script>

<template>
  <span class="decision-badge" :class="config.class">
    {{ config.icon }} {{ config.label }}
  </span>
</template>

<style scoped>
.decision-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 14px;
  border-radius: var(--radius-md, 12px);
  font-size: 0.88rem;
  font-weight: 600;
  letter-spacing: 0.02em;
}
.badge-bull {
  background: #ecfdf5;
  color: #065f46;
  border: 1px solid #a7f3d0;
}
.badge-neutral {
  background: #fffbeb;
  color: #92400e;
  border: 1px solid #fde68a;
}
.badge-bear {
  background: #fef2f2;
  color: #991b1b;
  border: 1px solid #fecaca;
}
</style>
