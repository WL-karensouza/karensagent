<!-- 模块9：散户实战操作指南 -->
<script setup>
defineProps({
  data: { type: Object, default: () => ({}) },
})
</script>

<template>
  <div v-if="data && Object.keys(data).length" class="m9-block">
    <h2 class="m9-title">🎯 散户实战操作指南</h2>

    <!-- 历史对比块：有变动 → 标题 + 条目列表 -->
    <div v-if="data.history_changes && data.history_changes.length" class="m9-history">
      <div class="m9-history-title">
        历史对比（基准：{{ data.history_anchor || '上期' }} 报告）
      </div>
      <ul class="m9-history-list">
        <li v-for="(item, i) in data.history_changes" :key="i">{{ item }}</li>
      </ul>
    </div>

    <!-- 历史对比块：无重大变化 -->
    <div v-else-if="data.history_compared" class="m9-history-nochange">
      与 {{ data.history_anchor || '上期' }} 报告对比无重大变化
    </div>

    <div class="m9-cols">
      <!-- 建仓策略 -->
      <div v-if="data.buy_strategy" class="m9-col buy">
        <span class="m9-col-icon">💡</span>
        <div class="m9-col-body">
          <span class="m9-col-label">建仓策略</span>
          <p class="m9-col-text">{{ data.buy_strategy }}</p>
        </div>
      </div>

      <!-- 止损参考 -->
      <div v-if="data.stop_loss" class="m9-col stop">
        <span class="m9-col-icon">🛑</span>
        <div class="m9-col-body">
          <span class="m9-col-label">止损参考</span>
          <p class="m9-col-text">{{ data.stop_loss }}</p>
        </div>
      </div>

      <!-- 止盈参考 -->
      <div v-if="data.take_profit" class="m9-col profit">
        <span class="m9-col-icon">🏆</span>
        <div class="m9-col-body">
          <span class="m9-col-label">止盈参考</span>
          <p class="m9-col-text">{{ data.take_profit }}</p>
        </div>
      </div>
    </div>

    <!-- 持有期建议 -->
    <div v-if="data.holding_period && Object.keys(data.holding_period).length" class="m9-holding">
      <span class="m9-holding-tag">{{ data.holding_period.type || '--' }}</span>
      <span v-if="data.holding_period.reason" class="m9-holding-reason">{{ data.holding_period.reason }}</span>
    </div>
  </div>
</template>

<style scoped>
/* 历史对比块：有变动 → 暖色底强调 */
.m9-history {
  padding: 14px 18px;
  background: #FEF3C7;
  border: 1px solid #FDE68A;
  border-radius: var(--radius-md);
  margin-bottom: 14px;
}
.m9-history-title {
  font-size: 0.85rem;
  font-weight: 700;
  color: #92400E;
  margin-bottom: 8px;
}
.m9-history-list {
  margin: 0;
  padding-left: 20px;
  list-style: disc;
}
.m9-history-list li {
  font-size: 0.82rem;
  color: #78350F;
  line-height: 1.7;
  margin-bottom: 4px;
}

/* 历史对比块：无重大变化 → 浅色小字 */
.m9-history-nochange {
  font-size: 0.78rem;
  color: var(--text-muted, #A8A29E);
  margin-bottom: 12px;
  padding: 0 2px;
}

/* 操作指南区块 */
.m9-block {
  padding: 22px 24px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  margin-bottom: 18px;
}
.m9-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 14px;
}
.m9-cols {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 14px;
}
.m9-col {
  display: flex;
  gap: 12px;
  padding: 14px 18px;
  border-radius: var(--radius-md);
  align-items: flex-start;
}
/* 三栏中性化：操作档位非多空信号，统一中性底 */
.m9-col.buy,
.m9-col.stop,
.m9-col.profit { background: var(--sent-bg); border: 1px solid var(--border-color); }
.m9-col-icon {
  font-size: 1.1rem;
  flex-shrink: 0;
  margin-top: 1px;
}
.m9-col-body { flex: 1; min-width: 0; }
.m9-col-label {
  font-size: 0.8rem;
  font-weight: 600;
  display: block;
  margin-bottom: 4px;
}
.m9-col-label { color: var(--sent-strong); }
.m9-col-text {
  margin: 0;
  font-size: 0.83rem;
  color: var(--text-secondary);
  line-height: 1.7;
}
.m9-holding {
  display: flex;
  align-items: baseline;
  gap: 12px;
  padding: 12px 18px;
  background: var(--sent-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}
.m9-holding-tag {
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--sent-strong);
  padding: 3px 12px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}
.m9-holding-reason {
  font-size: 0.83rem;
  color: var(--sent-mid);
  line-height: 1.6;
}
</style>
