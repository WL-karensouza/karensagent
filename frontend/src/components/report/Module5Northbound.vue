<!-- 模块5：北向资金/主力拆解 -->
<script setup>
defineProps({
  data: { type: Object, default: () => ({}) },
})
</script>

<template>
  <div v-if="data && Object.keys(data).length" class="m5-block">
    <h2 class="m5-title">🌏 北向资金 / 主力拆解</h2>

    <!-- 数据可用 -->
    <template v-if="data.available">
      <p v-if="data.trend" class="m5-trend">{{ data.trend }}</p>
      <p v-if="data.interpretation" class="m5-interp">{{ data.interpretation }}</p>
    </template>

    <!-- 数据不可用 -->
    <p v-else class="m5-unavailable">⚠️ 北向资金数据暂不可用</p>
  </div>
</template>

<style scoped>
/* 北向资金区块 */
.m5-block {
  padding: 22px 24px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  margin-bottom: 18px;
}
.m5-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 12px;
}
.m5-trend {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 10px;
  line-height: 1.7;
}
.m5-interp {
  font-size: 0.84rem;
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.8;
}
.m5-unavailable {
  font-size: 0.84rem;
  color: var(--text-muted);
  margin: 0;
  padding: 16px;
  text-align: center;
  background: var(--bg-hover, #f9fafb);
  border-radius: var(--radius-md);
}
</style>
