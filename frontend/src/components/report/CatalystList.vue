<!-- 模块7：催化剂与近期舆情 -->
<script setup>
import { sentimentColor } from '../../utils/stock.js'

defineProps({
  data: { type: Object, default: () => ({}) },
})
</script>

<template>
  <div v-if="data && Object.keys(data).length" class="m7-block">
    <h2 class="m7-title">📰 催化剂与近期舆情</h2>

    <!-- 舆情风向标 -->
    <div v-if="data.sentiment" class="m7-sentiment">
      <span class="m7-sentiment-tag" :style="{ color: sentimentColor(data.sentiment) }">{{ data.sentiment }}</span>
      <span v-if="data.sentiment_reason" class="m7-sentiment-reason">{{ data.sentiment_reason }}</span>
    </div>

    <!-- 两栏：利好 + 利空 -->
    <div class="m7-cols">
      <!-- 利好催化 -->
      <div v-if="data.positive && data.positive.length" class="m7-col positive">
        <h4 class="m7-col-title">🟢 利好催化</h4>
        <ul>
          <li v-for="(p, i) in data.positive" :key="i">{{ p }}</li>
        </ul>
      </div>

      <!-- 利空预警 -->
      <div v-if="data.negative && data.negative.length" class="m7-col negative">
        <h4 class="m7-col-title">🔴 利空预警</h4>
        <ul>
          <li v-for="(n, i) in data.negative" :key="i">{{ n }}</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 催化舆情区块 */
.m7-block {
  padding: 22px 24px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  margin-bottom: 18px;
}
.m7-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 14px;
}
.m7-sentiment {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.m7-sentiment-tag {
  font-size: 0.78rem;
  font-weight: 600;
  padding: 3px 12px;
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}
/* 舆情风向标 tag 中性底，方向色由内联 style 给 */
.m7-sentiment-tag { background: var(--sent-bg); border: 1px solid var(--border-color); }
.m7-sentiment-reason {
  font-size: 0.82rem;
  color: var(--text-muted);
}
.m7-cols {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.m7-col {
  padding: 16px 18px;
  border-radius: var(--radius-md);
}
/* 利好/利空两栏中性底，方向色落在标题与列表项 */
.m7-col.positive,
.m7-col.negative {
  background: var(--sent-bg);
  border: 1px solid var(--border-color);
}
.m7-col-title {
  font-size: 0.82rem;
  font-weight: 600;
  margin: 0 0 8px;
}
.positive .m7-col-title { color: var(--red); }
.negative .m7-col-title { color: var(--green); }
.m7-col ul {
  margin: 0;
  padding-left: 18px;
}
.m7-col li {
  font-size: 0.81rem;
  margin: 4px 0;
  line-height: 1.6;
}
/* .positive li { color: var(--red); }
.negative li { color: var(--green); } */
</style>
