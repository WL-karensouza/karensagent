<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useStockStore } from '../../stores/stock.js'
import { scoreColor, decisionBadge } from '../../utils/stock.js'

const router = useRouter()
const store = useStockStore()
const stockCode = ref('')

onMounted(() => {
  store.fetchWatchlist()
  store.fetchDashboardReports()
})

async function handleAnalyze() {
  const code = stockCode.value.trim()
  if (!code) {
    store.showToast('请输入股票代码')
    return
  }
  await store.triggerAnalyze(code)
}

function goReport(id) {
  if (!id || id <= 0) return
  router.push(`/agent/stock/report/${id}`)
}

function goHistory() {
  router.push('/agent/stock/history')
}

function goSettings() {
  router.push('/agent/stock/settings')
}

</script>

<template>
  <div>
    <div class="page-header">
      <h1>股票分析</h1>
      <p>AI 驱动的 A 股多维度分析引擎</p>
    </div>

    <!-- 搜索分析栏 -->
    <div class="card" style="margin-bottom:24px;">
      <div style="display:flex;gap:12px;align-items:center;">
        <input
          v-model="stockCode"
          class="form-input"
          placeholder="输入 A 股代码，如 600519..."
          style="flex:1;max-width:320px;"
          @keyup.enter="handleAnalyze"
        />
        <button
          class="btn btn-primary"
          :disabled="store.analyzing"
          @click="handleAnalyze"
        >
          <span v-if="store.analyzing" class="spinner" style="width:16px;height:16px;border-width:2px;"></span>
          {{ store.analyzing ? '分析中...' : '开始分析' }}
        </button>
      </div>

      <!-- 分析结果摘要 -->
      <div v-if="store.analyzeResult && store.analyzeResult.report" style="margin-top:16px;">
        <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
          <span style="font-weight:600;">{{ store.analyzeResult.report.stock_name || '' }}</span>
          <span style="font-size:1.5rem;font-weight:700;" :style="{color: scoreColor(store.analyzeResult.report.score)}">
            {{ store.analyzeResult.report.score }} 分
          </span>
          <span class="tag active">{{ decisionBadge(store.analyzeResult.report.decision) }}</span>
          <button
            v-if="store.analyzeResult.report_id"
            class="btn btn-outline btn-sm"
            @click="goReport(store.analyzeResult.report_id)"
          >
            查看完整报告 →
          </button>
        </div>
        <p style="margin-top:8px;color:var(--text-secondary);font-size:0.9rem;">
          {{ store.analyzeResult.report.summary || '' }}
        </p>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon">📊</div>
        <div class="stat-value">{{ store.dashboardReportsTotal }}</div>
        <div class="stat-label">历史报告总数</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">⭐</div>
        <div class="stat-value">{{ store.watchlist.length }}</div>
        <div class="stat-label">自选股数量</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">🕐</div>
        <div class="stat-value" style="font-size:1.2rem;">
          {{ store.dashboardReports.length > 0 ? store.dashboardReports[0].created_at?.slice(0, 10) : '暂无' }}
        </div>
        <div class="stat-label">最近分析日期</div>
      </div>
    </div>

    <!-- 快捷操作 + 自选股 -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-bottom:24px;">
      <!-- 快捷操作 -->
      <div class="card">
        <h3 style="margin-bottom:16px;font-size:1rem;">⚡ 快捷操作</h3>
        <div style="display:flex;gap:12px;flex-wrap:wrap;">
          <button class="btn btn-outline btn-sm" @click="router.push('/agent/stock/settings')">
            管理自选股
          </button>
          <button class="btn btn-outline btn-sm" @click="goHistory">
            查看历史报告
          </button>
          <button class="btn btn-outline btn-sm" @click="store.triggerWatchlistAnalyze()">
            📊 自选股分析
          </button>
        </div>
      </div>

      <!-- 自选股列表 -->
      <div class="card">
        <h3 style="margin-bottom:16px;font-size:1rem;">⭐ 我的自选股</h3>
        <div v-if="store.watchlist.length === 0" style="color:var(--text-muted);text-align:center;padding:20px;">
          暂无自选股，<a href="#" @click.prevent="goSettings">去添加</a>
        </div>
        <div v-else style="display:flex;flex-direction:column;gap:8px;">
          <div
            v-for="item in store.watchlist"
            :key="item.stock_code"
            style="display:flex;align-items:center;justify-content:space-between;padding:8px 12px;background:var(--bg-subtle);border-radius:var(--radius-sm);"
          >
            <div>
              <span style="font-weight:600;">{{ item.stock_name || item.stock_code }}</span>
              <span style="color:var(--text-muted);font-size:0.8rem;margin-left:8px;">{{ item.stock_code }}</span>
            </div>
            <button
              class="btn btn-outline btn-sm"
              @click="stockCode = item.stock_code; handleAnalyze()"
            >
              分析
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 最近报告 -->
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
        <h3 style="font-size:1rem;">📋 最近分析报告</h3>
        <button class="btn btn-outline btn-sm" @click="goHistory">查看全部 →</button>
      </div>
      <div v-if="store.dashboardReports.length === 0" class="empty-state" style="padding:40px;">
        <p>暂无报告，输入股票代码开始分析</p>
      </div>
      <table v-else class="data-table">
        <thead>
          <tr>
            <th>股票</th>
            <th>代码</th>
            <th>评分</th>
            <th>判断</th>
            <th>时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in store.dashboardReports" :key="r.id">
            <td style="font-weight:600;">{{ r.stock_name }}</td>
            <td>{{ r.stock_code }}</td>
            <td>
              <span :style="{color: scoreColor(r.score), fontWeight: 700, fontSize: '1.1rem'}">{{ r.score }}</span>
            </td>
            <td><span class="tag active">{{ decisionBadge(r.decision) }}</span></td>
            <td style="color:var(--text-secondary);font-size:0.85rem;">{{ r.created_at?.slice(0, 16) }}</td>
            <td>
              <button class="btn btn-outline btn-sm" @click="goReport(r.id)">查看</button>
              <button class="btn btn-outline btn-sm" style="margin-left:6px;" @click="store.pushToFeishu(r.id)">📤 推送</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
