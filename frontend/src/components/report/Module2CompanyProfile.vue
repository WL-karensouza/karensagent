<!-- 模块2：公司画像与估值定位 -->
<script setup>
import { peLevelSym, peLevelColor } from '../../utils/stock.js'

defineProps({
  data: { type: Object, default: () => ({}) },
})
</script>

<template>
  <div v-if="data && Object.keys(data).length" class="m2-block">
    <h2 class="m2-title">🏢 公司画像与估值定位</h2>

    <!-- 主营业务 -->
    <p v-if="data.business" class="m2-business">{{ data.business }}</p>

    <!-- 估值水位 -->
    <div v-if="data.valuation && Object.keys(data.valuation).length" class="m2-val">
      <div class="m2-val-row">
        <span class="m2-val-label">PE 估值水位</span>
        <span class="m2-val-tag" :style="{ color: peLevelColor(data.valuation.pe_level) }">{{ peLevelSym(data.valuation.pe_level) }} {{ data.valuation.pe_level || 'N/A' }}</span>
      </div>
      <div class="m2-val-row">
        <span class="m2-val-label">PB 估值水位</span>
        <span class="m2-val-tag" :style="{ color: peLevelColor(data.valuation.pb_level) }">{{ peLevelSym(data.valuation.pb_level) }} {{ data.valuation.pb_level || 'N/A' }}</span>
      </div>
      <p v-if="data.valuation.analysis" class="m2-analysis">{{ data.valuation.analysis }}</p>
    </div>
  </div>
</template>

<style scoped>
/* 公司画像区块 */
.m2-block {
  padding: 22px 24px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  margin-bottom: 18px;
}
.m2-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 14px;
}
.m2-business {
  font-size: 0.85rem;
  color: var(--text-secondary);
  line-height: 1.8;
  margin: 0 0 16px;
}
.m2-val {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.m2-val-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.m2-val-label {
  font-size: 0.82rem;
  color: var(--text-muted);
  width: 90px;
  flex-shrink: 0;
}
.m2-val-tag {
  font-size: 0.78rem;
  font-weight: 600;
  padding: 3px 12px;
  border-radius: var(--radius-sm, 6px);
}
/* 估值水位 tag 统一中性底，方向色由内联 style 给 */
.m2-val-tag { background: var(--sent-bg); border: 1px solid var(--border-color); }
.m2-analysis {
  margin: 4px 0 0;
  font-size: 0.84rem;
  color: var(--text-secondary);
  line-height: 1.75;
}
</style>
