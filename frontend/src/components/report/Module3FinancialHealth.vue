<!-- 模块3：财务健康状况 -->
<script setup>
defineProps({
  data: { type: Object, default: () => ({}) },
})
</script>

<template>
  <div v-if="data && Object.keys(data).length" class="m3-block">
    <h2 class="m3-title">💰 财务健康状况</h2>

    <!-- 赚钱能力一句话 -->
    <p v-if="data.profitability" class="m3-profit">{{ data.profitability }}</p>

    <!-- 核心指标表格 -->
    <div v-if="data.key_indicators && data.key_indicators.length" class="m3-table-wrap">
      <table class="m3-table">
        <thead>
          <tr>
            <th>指标</th>
            <th>数值</th>
            <th>趋势</th>
            <th>解读</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(ind, i) in data.key_indicators" :key="i">
            <td class="m3-td-name">{{ ind.name }}</td>
            <td class="m3-td-val">{{ ind.value }}</td>
            <td>
              <span class="m3-trend" :class="{
                'trend-up': ind.trend && (ind.trend.includes('上升') || ind.trend.includes('改善')),
                'trend-down': ind.trend && (ind.trend.includes('下滑') || ind.trend.includes('恶化')),
              }">{{ ind.trend }}</span>
            </td>
            <td class="m3-td-verdict">{{ ind.verdict }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 排雷提示 -->
    <div v-if="data.risk_alerts && data.risk_alerts.length" class="m3-alerts">
      <h4 class="m3-alert-title">⚠️ 财务排雷</h4>
      <ul>
        <li v-for="(a, i) in data.risk_alerts" :key="i">{{ a }}</li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
/* 财务健康区块 */
.m3-block {
  padding: 22px 24px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  margin-bottom: 18px;
}
.m3-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 12px;
}
.m3-profit {
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 16px;
  line-height: 1.7;
}
.m3-table-wrap {
  overflow-x: auto;
  margin-bottom: 14px;
}
.m3-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8rem;
}
.m3-table th {
  text-align: left;
  padding: 8px 10px;
  background: var(--bg-hover, #f3f4f6);
  color: var(--text-muted);
  font-weight: 600;
  white-space: nowrap;
}
.m3-table td {
  padding: 8px 10px;
  border-bottom: 1px solid var(--border-color);
  color: var(--text-secondary);
  line-height: 1.55;
}
.m3-td-name { font-weight: 600; color: var(--text-primary); }
.m3-td-val { font-family: 'JetBrains Mono', monospace; }
.m3-td-verdict { font-size: 0.78rem; }
.m3-trend {
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: var(--radius-sm, 4px);
  white-space: nowrap;
  background: #f3f4f6;
  color: var(--text-muted);
}
.trend-up { background: #ecfdf5; color: #065f46; }
.trend-down { background: #fef2f2; color: #991b1b; }
.m3-alerts {
  padding: 14px 18px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: var(--radius-md);
}
.m3-alert-title {
  font-size: 0.82rem;
  font-weight: 600;
  color: #991b1b;
  margin: 0 0 8px;
}
.m3-alerts ul {
  margin: 0;
  padding-left: 18px;
}
.m3-alerts li {
  font-size: 0.81rem;
  color: #7f1d1d;
  margin: 4px 0;
  line-height: 1.6;
}
</style>
