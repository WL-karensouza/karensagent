<!-- 模块9：散户实战操作指南 -->
<script setup>
defineProps({
  data: { type: Object, default: () => ({}) },
})
</script>

<template>
  <div v-if="data && Object.keys(data).length" class="m9-block">
    <h2 class="m9-title">🎯 散户实战操作指南</h2>

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
.m9-col.buy { background: #eff6ff; border: 1px solid #bfdbfe; }
.m9-col.stop { background: #fef2f2; border: 1px solid #fecaca; }
.m9-col.profit { background: #ecfdf5; border: 1px solid #a7f3d0; }
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
.buy .m9-col-label { color: #1e40af; }
.stop .m9-col-label { color: #991b1b; }
.profit .m9-col-label { color: #065f46; }
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
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: var(--radius-md);
}
.m9-holding-tag {
  font-size: 0.8rem;
  font-weight: 700;
  color: #92400e;
  padding: 3px 12px;
  background: #fef3c7;
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}
.m9-holding-reason {
  font-size: 0.83rem;
  color: #78350f;
  line-height: 1.6;
}
</style>
