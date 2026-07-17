<!-- 模块2：公司画像与估值定位 -->
<script setup>
import { computed } from 'vue'

const props = defineProps({
  data: { type: Object, default: () => ({}) },
})

const peTheme = computed(() => {
  const map = { '偏低': 'low', '合理': 'fair', '偏高': 'high', '极度偏高': 'extreme' }
  return map[props.data?.valuation?.pe_level] || 'fair'
})
const pbTheme = computed(() => {
  const map = { '偏低': 'low', '合理': 'fair', '偏高': 'high', '极度偏高': 'extreme' }
  return map[props.data?.valuation?.pb_level] || 'fair'
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
        <span class="m2-val-tag" :class="'tag-' + peTheme">{{ data.valuation.pe_level || 'N/A' }}</span>
      </div>
      <div class="m2-val-row">
        <span class="m2-val-label">PB 估值水位</span>
        <span class="m2-val-tag" :class="'tag-' + pbTheme">{{ data.valuation.pb_level || 'N/A' }}</span>
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
.tag-low { background: #ecfdf5; color: #065f46; border: 1px solid #a7f3d0; }
.tag-fair { background: #fffbeb; color: #92400e; border: 1px solid #fde68a; }
.tag-high { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }
.tag-extreme { background: #fef2f2; color: #7f1d1d; border: 1px solid #f87171; }
.m2-analysis {
  margin: 4px 0 0;
  font-size: 0.84rem;
  color: var(--text-secondary);
  line-height: 1.75;
}
</style>
