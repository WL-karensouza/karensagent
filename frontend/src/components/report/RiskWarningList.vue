<!-- 模块8：风险评估与ESG表现 -->
<script setup>
defineProps({
  data: { type: Object, default: () => ({}) },
})
</script>

<template>
  <div v-if="data && Object.keys(data).length" class="m8-block">
    <h2 class="m8-title">
      ⚠️ 风险评估与 ESG 表现
      <span v-if="data.risk_level" class="m8-level-tag" :class="{
        'level-low': data.risk_level === '低',
        'level-mid': data.risk_level === '中',
        'level-high': data.risk_level === '高',
      }">风险等级：{{ data.risk_level }}</span>
    </h2>

    <!-- 风险列表 -->
    <div v-if="data.risks && data.risks.length" class="m8-risks">
      <div v-for="(r, i) in data.risks" :key="i" class="m8-risk-item" :class="{
        'risk-high': r.level === '高',
        'risk-mid': r.level === '中',
        'risk-low': r.level === '低',
      }">
        <span class="m8-risk-badge" :class="{
          'badge-high': r.level === '高',
          'badge-mid': r.level === '中',
          'badge-low': r.level === '低',
        }">{{ r.level || '?' }}</span>
        <div class="m8-risk-body">
          <span class="m8-risk-type">{{ r.type }}</span>
          <p class="m8-risk-desc">{{ r.desc }}</p>
        </div>
      </div>
    </div>

    <!-- ESG 解读 -->
    <blockquote v-if="data.esg" class="m8-esg">
      <p>{{ data.esg }}</p>
    </blockquote>
  </div>
</template>

<style scoped>
/* 风险ESG区块 */
.m8-block {
  padding: 22px 24px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  margin-bottom: 18px;
}
.m8-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 14px;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.m8-level-tag {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: var(--radius-sm);
}
.level-low { background: #ecfdf5; color: #065f46; border: 1px solid #a7f3d0; }
.level-mid { background: #fffbeb; color: #92400e; border: 1px solid #fde68a; }
.level-high { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }

.m8-risks {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 14px;
}
.m8-risk-item {
  display: flex;
  gap: 12px;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  background: var(--bg-hover, #f9fafb);
}
.risk-high { border-left: 3px solid #ef4444; }
.risk-mid { border-left: 3px solid #f59e0b; }
.risk-low { border-left: 3px solid #10b981; }
.m8-risk-badge {
  flex-shrink: 0;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  font-size: 0.7rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 1px;
}
.badge-high { background: #fef2f2; color: #dc2626; }
.badge-mid { background: #fffbeb; color: #d97706; }
.badge-low { background: #ecfdf5; color: #059669; }
.m8-risk-body {
  flex: 1;
  min-width: 0;
}
.m8-risk-type {
  font-size: 0.83rem;
  font-weight: 600;
  color: var(--text-primary);
}
.m8-risk-desc {
  margin: 4px 0 0;
  font-size: 0.8rem;
  color: var(--text-muted);
  line-height: 1.6;
}
.m8-esg {
  padding: 16px 20px;
  margin: 0;
  background: var(--bg-subtle, #f8f7f4);
  border-left: 3px solid var(--accent, #D97706);
  border-radius: 0 var(--radius-sm, 8px) var(--radius-sm, 8px) 0;
}
.m8-esg p {
  margin: 0;
  font-size: 0.84rem;
  color: var(--text-secondary);
  line-height: 1.75;
}
</style>
