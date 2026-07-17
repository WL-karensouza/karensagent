<script setup>
/* 通用空状态组件 — 任一维度数据缺失时调用 */
defineProps({
  dimLabel: { type: String, default: '该维度' },
})
</script>

<template>
  <div class="empty-state">
    <div class="empty-stamp">Data Unavailable</div>
    <h4>{{ dimLabel }}数据暂未收录</h4>
    <p>iFind 对应接口返回空数据，可能原因：该股票暂未覆盖此维度数据。</p>
  </div>
</template>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 40px;
  text-align: center;
}
.empty-stamp {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  color: var(--dash-red);
  border: 2px dashed var(--dash-red);
  padding: 8px 16px;
  border-radius: var(--dash-radius-sm);
  transform: rotate(-3deg);
  opacity: 0.8;
  margin-bottom: 16px;
}
.empty-state h4 {
  font-size: 1rem;
  font-weight: 600;
  color: var(--ink-secondary);
  margin-bottom: 6px;
}
.empty-state p {
  font-size: 0.82rem;
  color: var(--ink-tertiary);
  max-width: 300px;
}
</style>
