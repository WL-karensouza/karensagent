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
/* 风险等级中性底，严重度由文字灰阶深浅区分（不上红绿） */
.m8-level-tag { background: var(--sent-bg); border: 1px solid var(--border-color); }
.level-low { color: var(--sent-soft); }
.level-mid { color: var(--sent-mid); }
.level-high { color: var(--sent-strong); }

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
/* 风险条目左侧条中性灰阶（高深/中/低浅），不用彩色 */
/* .risk-high { border-left: 3px solid var(--sent-strong); }
.risk-mid { border-left: 3px solid var(--sent-mid); }
.risk-low { border-left: 3px solid var(--sent-soft); } */
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
/* 风险徽章中性底，严重度由文字灰阶区分 */
.m8-risk-badge { background: var(--sent-bg); }
/* .badge-high { color: var(--sent-strong); }
.badge-mid { color: var(--sent-mid); }
.badge-low { color: var(--sent-soft); } */
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
  background: var(--sent-bg);
  border-radius: var(--radius-sm, 8px);
}
.m8-esg p {
  margin: 0;
  font-size: 0.84rem;
  color: var(--text-secondary);
  line-height: 1.75;
}
</style>
