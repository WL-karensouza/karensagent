<!-- 信号归因权重表 -->
<script setup>
import { attrColor } from '../../utils/stock.js'

defineProps({
  attribution: { type: Array, default: () => [] },
})
</script>

<template>
  <div v-if="attribution.length" class="attr-block">
    <h3 class="attr-title">📊 信号归因</h3>
    <div class="attr-table">
      <div v-for="item in attribution" :key="item.source" class="attr-row">
        <span class="attr-source">{{ item.source }}</span>
        <div class="attr-bar-wrap">
          <div
            class="attr-bar"
            :style="{
              width: (item.weight * 100) + '%',
              background: attrColor(item.direction)
            }"
          ></div>
        </div>
        <span class="attr-weight">{{ (item.weight * 100).toFixed(0) }}%</span>
        <span class="attr-dir" :style="{ color: attrColor(item.direction) }">
          {{ item.direction }}
        </span>
      </div>
    </div>
    <!-- 归因说明 -->
    <div class="attr-notes">
      <span v-for="item in attribution" :key="'n-'+item.source" class="attr-note">
        {{ item.note }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.attr-block {
  padding: 20px 22px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  margin-bottom: 18px;
}
.attr-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 14px;
}
.attr-table {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}
.attr-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.attr-source {
  width: 72px;
  flex-shrink: 0;
  font-size: 0.78rem;
  color: var(--text-secondary);
}
.attr-bar-wrap {
  flex: 1;
  height: 8px;
  background: var(--bg-hover);
  border-radius: 4px;
  overflow: hidden;
}
.attr-bar {
  height: 100%;
  border-radius: 4px;
  transition: width 0.4s ease;
  min-width: 2px;
}
.attr-weight {
  width: 36px;
  text-align: right;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--text-primary);
  font-family: 'JetBrains Mono', monospace;
}
.attr-dir {
  width: 32px;
  font-size: 0.72rem;
  text-align: center;
  padding: 1px 6px;
  border-radius: 4px;
}
/* 方向文字色由内联 style 给，标签统一中性底 */
.attr-dir { background: var(--sent-bg); }

.attr-notes {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.attr-note {
  font-size: 0.78rem;
  color: var(--text-muted);
}
.attr-note::before {
  content: '• ';
  color: var(--sent-mid);
}
</style>
