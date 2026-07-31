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
      <span v-if="data.reference_prices.support" class="m1-price">
        <span style="color: var(--red)">↑</span> 支撑位：{{ data.reference_prices.support }}
      </span>
      <span v-if="data.reference_prices.resistance" class="m1-price">
        <span style="color: var(--green)">↓</span> 压力位：{{ data.reference_prices.resistance }}
      </span>
    </div>
  </div>
</template>

<style scoped>
/* 核心结论区块 */
.m1-block {
  margin-bottom: 24px;
}
/* 一句话评级：中性底，去左竖杠，四角圆角 */
.m1-rating {
  padding: 20px 24px;
  margin: 0;
  background: var(--sent-bg);
  border-radius: var(--radius-sm, 8px);
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
/* 支撑/压力 chip 统一中性底，箭头颜色由内联 style 给 */
.m1-price {
  background: var(--bg-card);
  color: var(--sent-strong);
  border: 1px solid var(--border-color);
}
</style>
