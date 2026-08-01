<!-- 模块6：股东结构与筹码集中度 -->
<script setup>
defineProps({
  data: { type: Object, default: () => ({}) },
})

const signalEmoji = (s) => ({ '偏多': '🟢', '偏空': '🔴', '中性': '⚪' })[s] || '⚪'
</script>

<template>
  <div v-if="data && Object.keys(data).length" class="m6-block">
    <h2 class="m6-title">👥 股东结构与筹码集中度</h2>

    <!-- 增减持动向 -->
    <div v-if="data.major_moves && data.major_moves.length" class="m6-moves">
      <h4 class="m6-subtitle">重要增减持动向</h4>
      <div v-for="(mv, i) in data.major_moves" :key="i" class="m6-move">
        <span class="m6-move-emoji">{{ signalEmoji(mv.signal) }}</span>
        <div class="m6-move-body">
          <span class="m6-move-entity">{{ mv.entity }}</span>
          <span class="m6-move-action">{{ mv.action }}</span>
          <span v-if="mv.date" class="m6-move-date">{{ mv.date }}</span>
        </div>
        <p v-if="mv.reason" class="m6-move-reason">{{ mv.reason }}</p>
      </div>
    </div>

    <!-- 筹码分析 -->
    <blockquote v-if="data.chip_analysis" class="m6-chip">
      <p>{{ data.chip_analysis }}</p>
    </blockquote>
  </div>
</template>

<style scoped>
/* 股东筹码区块 */
.m6-block {
  padding: 22px 24px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  margin-bottom: 18px;
}
.m6-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 12px;
}
.m6-subtitle {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--text-muted);
  margin: 0 0 10px;
}
.m6-moves {
  margin-bottom: 14px;
}
.m6-move {
  display: grid;
  grid-template-columns: 24px 1fr;
  gap: 6px 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-color);
}
.m6-move:last-child { border-bottom: none; }
.m6-move-emoji {
  font-size: 0.85rem;
  line-height: 1.5;
}
.m6-move-body {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: baseline;
}
.m6-move-entity { font-weight: 600; font-size: 0.83rem; color: var(--text-primary); }
.m6-move-action { font-size: 0.82rem; color: var(--text-secondary); }
.m6-move-date { font-size: 0.75rem; color: var(--text-muted); }
.m6-move-reason {
  grid-column: 2;
  margin: 0;
  font-size: 0.8rem;
  color: var(--text-muted);
  line-height: 1.55;
}
.m6-chip {
  padding: 16px 20px;
  margin: 0;
  background: var(--bg-subtle, #f8f7f4);
  /* border-left: 3px solid var(--accent, #D97706); */
  border-radius: 0 var(--radius-sm, 8px) var(--radius-sm, 8px) 0;
}
.m6-chip p {
  margin: 0;
  font-size: 0.84rem;
  color: var(--text-secondary);
  line-height: 1.75;
}
</style>
