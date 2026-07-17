<!-- 模块4：股价走势与资金动向 -->
<script setup>
defineProps({
  data: { type: Object, default: () => ({}) },
})
</script>

<template>
  <div v-if="data && Object.keys(data).length" class="m4-block">
    <h2 class="m4-title">📈 股价走势与资金动向</h2>

    <!-- 趋势描述 -->
    <p v-if="data.trend" class="m4-trend">{{ data.trend }}</p>

    <!-- 资金面 -->
    <div v-if="data.capital_flow && Object.keys(data.capital_flow).length" class="m4-flow">
      <div v-if="data.capital_flow.margin_trading" class="m4-flow-item margin">
        <span class="m4-flow-label">融资融券</span>
        <span class="m4-flow-text">{{ data.capital_flow.margin_trading }}</span>
      </div>
      <div v-if="data.capital_flow.main_force" class="m4-flow-item force">
        <span class="m4-flow-label">主力资金</span>
        <span class="m4-flow-text">{{ data.capital_flow.main_force }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 股价走势区块 */
.m4-block {
  padding: 22px 24px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  margin-bottom: 18px;
}
.m4-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 12px;
}
.m4-trend {
  font-size: 0.85rem;
  color: var(--text-secondary);
  line-height: 1.8;
  margin: 0 0 16px;
}
.m4-flow {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.m4-flow-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 16px;
  border-radius: var(--radius-md);
}
.m4-flow-item.margin {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
}
.m4-flow-item.force {
  background: #f3e8ff;
  border: 1px solid #e9d5ff;
}
.m4-flow-label {
  flex-shrink: 0;
  font-size: 0.78rem;
  font-weight: 600;
  padding: 2px 10px;
  border-radius: var(--radius-sm);
  white-space: nowrap;
}
.margin .m4-flow-label { background: #dbeafe; color: #1e40af; }
.force .m4-flow-label { background: #ede9fe; color: #6b21a8; }
.m4-flow-text {
  font-size: 0.83rem;
  color: var(--text-secondary);
  line-height: 1.6;
}
</style>
