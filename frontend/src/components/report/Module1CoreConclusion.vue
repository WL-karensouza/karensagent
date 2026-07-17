<!-- 模块1：核心结论与操作建议 -->
<script setup>
defineProps({
  data: { type: Object, default: () => ({}) },
})
</script>

<template>
  <div v-if="data && Object.keys(data).length" class="m1-block">
    <!-- 一句话评级 -->
    <blockquote v-if="data.rating_sentence" class="m1-rating">
      <p>{{ data.rating_sentence }}</p>
    </blockquote>

    <!-- 核心逻辑 -->
    <ul v-if="data.core_logic && data.core_logic.length" class="m1-logic">
      <li v-for="(point, i) in data.core_logic" :key="i">{{ point }}</li>
    </ul>

    <!-- 参考价位 -->
    <div v-if="data.reference_prices" class="m1-prices">
      <span v-if="data.reference_prices.support" class="m1-price support">
        🟢 支撑位：{{ data.reference_prices.support }}
      </span>
      <span v-if="data.reference_prices.resistance" class="m1-price resistance">
        🔴 压力位：{{ data.reference_prices.resistance }}
      </span>
    </div>
  </div>
</template>

<style scoped>
/* 核心结论区块 */
.m1-block {
  margin-bottom: 24px;
}
.m1-rating {
  padding: 20px 24px;
  margin: 0;
  background: var(--bg-subtle, #f8f7f4);
  border-left: 3px solid var(--accent, #D97706);
  border-radius: 0 var(--radius-sm, 8px) var(--radius-sm, 8px) 0;
}
.m1-rating p {
  margin: 0;
  font-size: 0.92rem;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.8;
}
.m1-logic {
  margin: 14px 0 0;
  padding-left: 20px;
}
.m1-logic li {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin: 6px 0;
  line-height: 1.7;
}
.m1-prices {
  display: flex;
  gap: 16px;
  margin-top: 12px;
}
.m1-price {
  font-size: 0.82rem;
  padding: 6px 14px;
  border-radius: var(--radius-md, 12px);
  font-weight: 500;
}
.m1-price.support {
  background: #ecfdf5;
  color: #065f46;
  border: 1px solid #a7f3d0;
}
.m1-price.resistance {
  background: #fef2f2;
  color: #991b1b;
  border: 1px solid #fecaca;
}
</style>
