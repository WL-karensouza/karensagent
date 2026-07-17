<script setup>
import { onMounted, computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useStockStore } from '../../stores/stock.js'
import { scoreColor } from '../../utils/stock.js'
import ScoreGauge from '../../components/report/ScoreGauge.vue'
import DecisionBadge from '../../components/report/DecisionBadge.vue'
import Module1CoreConclusion from '../../components/report/Module1CoreConclusion.vue'
import Module2CompanyProfile from '../../components/report/Module2CompanyProfile.vue'
import Module3FinancialHealth from '../../components/report/Module3FinancialHealth.vue'
import Module4PriceTrend from '../../components/report/Module4PriceTrend.vue'
import Module5Northbound from '../../components/report/Module5Northbound.vue'
import Module6Shareholders from '../../components/report/Module6Shareholders.vue'
import CatalystList from '../../components/report/CatalystList.vue'
import RiskWarningList from '../../components/report/RiskWarningList.vue'
import HoldingAdviceCard from '../../components/report/HoldingAdviceCard.vue'
import SignalAttribution from '../../components/report/SignalAttribution.vue'
import ReportMeta from '../../components/report/ReportMeta.vue'

const route = useRoute()
const router = useRouter()
const store = useStockStore()
const reportId = computed(() => route.params.id)
const mounted = ref(false)

onMounted(() => {
  const id = Number(reportId.value)
  if (!id || id <= 0) {
    store.showToast('无效的报告 ID')
    router.replace('/agent/stock')
    return
  }
  store.fetchReportDetail(id).finally(() => {
    mounted.value = true
  })
})

/* 结构化报告数据 */
const reportData = computed(() => {
  const row = store.currentReport
  if (!row) return null
  try {
    if (typeof row.report_json === 'string') return JSON.parse(row.report_json)
    return row.report_json
  } catch {
    return null
  }
})

async function handlePush() {
  const row = store.currentReport
  if (!row) return
  await store.pushToFeishu(row.id)
}
</script>

<template>
  <div class="report-page">
    <!-- 返回导航 -->
    <button class="btn-back" @click="router.push('/agent/stock')">
      ← 返回仪表盘
    </button>

    <h1 v-if="store.currentReport" class="report-title">
      {{ store.currentReport.stock_name }}（{{ store.currentReport.stock_code }}）
    </h1>

    <!-- 加载中 -->
    <div v-if="!mounted || store.reportLoading" class="loading-box">
      <span class="spinner"></span> 加载报告...
    </div>

    <!-- 加载出错 -->
    <div v-else-if="store.reportError && !store.currentReport" class="error-box">
      <p>{{ store.reportError }}</p>
      <button class="btn-search" style="margin-top:12px;" @click="store.fetchReportDetail(reportId)">重试</button>
    </div>

    <!-- 无数据 -->
    <div v-else-if="!store.currentReport" class="error-box">
      <p>报告不存在</p>
    </div>

    <template v-else-if="reportData">
      <!-- ===== 评分概览区 ===== -->
      <div class="score-card">
        <ScoreGauge :score="reportData.score" :size="130" />
        <div class="score-info">
          <DecisionBadge :decision="reportData.decision" />
          <p class="score-desc">
            综合评分 <strong :style="{ color: scoreColor(reportData.score) }">{{ reportData.score }}</strong> / 100
          </p>
          <button class="btn-search" @click="handlePush">📤 推送飞书</button>
        </div>
      </div>

      <!-- ===== 模块1：核心结论与操作建议 ===== -->
      <Module1CoreConclusion :data="reportData.module_1_核心结论" />

      <!-- ===== 模块2：公司画像与估值定位 ===== -->
      <Module2CompanyProfile :data="reportData.module_2_公司画像" />

      <!-- ===== 模块3：财务健康状况 ===== -->
      <Module3FinancialHealth :data="reportData.module_3_财务健康" />

      <!-- ===== 模块4：股价走势与资金动向 ===== -->
      <Module4PriceTrend :data="reportData.module_4_股价走势" />

      <!-- ===== 模块5：北向资金/主力拆解 ===== -->
      <Module5Northbound :data="reportData.module_5_北向资金" />

      <!-- ===== 模块6：股东结构与筹码集中度 ===== -->
      <Module6Shareholders :data="reportData.module_6_股东筹码" />

      <!-- ===== 模块7：催化剂与近期舆情 ===== -->
      <CatalystList :data="reportData.module_7_催化舆情" />

      <!-- ===== 模块8：风险评估与ESG表现 ===== -->
      <RiskWarningList :data="reportData.module_8_风险ESG" />

      <!-- ===== 模块9：散户实战操作指南 ===== -->
      <HoldingAdviceCard :data="reportData.module_9_操作指南" />

      <!-- ===== 信号归因 ===== -->
      <SignalAttribution :attribution="reportData.signal_attribution" />

      <!-- ===== 元信息 ===== -->
      <ReportMeta
        :created-at="store.currentReport.created_at"
        :token-used="store.currentReport.token_used"
      />

      <!-- 追问输入框（v2 功能占位） -->
      <div class="followup-box">
        <input
          class="followup-input"
          type="text"
          placeholder="💬 对报告内容有疑问？在此追问 AI（即将上线）"
          disabled
        />
        <button class="btn-search" disabled>发送</button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.report-page {
  max-width: 860px;
  margin: 0 auto;
  padding: 32px 0 60px;
}

/* 返回按钮 */
.btn-back {
  display: inline-block;
  margin-bottom: 16px;
  border: none;
  background: none;
  color: var(--text-secondary);
  font-size: 0.82rem;
  font-family: inherit;
  cursor: pointer;
}
.btn-back:hover { color: var(--accent); }

/* 标题 */
.report-title {
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 24px;
}

/* 评分卡片 */
.score-card {
  display: flex;
  align-items: center;
  gap: 28px;
  padding: 28px 32px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  margin-bottom: 24px;
}
.score-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
}
.score-desc {
  font-size: 0.82rem;
  color: var(--text-muted);
  margin: 0;
}

/* 加载/错误 */
.loading-box, .error-box {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-muted);
}
.error-box p { color: var(--red); margin-bottom: 8px; }

.spinner {
  display: inline-block;
  width: 18px; height: 18px;
  border: 2px solid var(--border-color);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  vertical-align: middle;
  margin-right: 8px;
}
@keyframes spin { to { transform: rotate(360deg); } }

.btn-search {
  height: 36px;
  padding: 0 20px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  font-size: 0.82rem;
  font-family: inherit;
  color: var(--text-secondary);
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s ease;
}
.btn-search:hover { border-color: var(--accent); color: var(--accent); }
.btn-search:disabled { opacity: 0.45; cursor: not-allowed; }

/* 追问输入框 */
.followup-box {
  display: flex;
  gap: 10px;
  margin-top: 24px;
  padding: 16px 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}
.followup-input {
  flex: 1;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 10px 14px;
  font-size: 0.85rem;
  font-family: inherit;
  color: var(--text-primary);
  background: var(--bg-subtle);
  outline: none;
}
.followup-input:disabled { color: var(--text-muted); cursor: not-allowed; }
</style>
