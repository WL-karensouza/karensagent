<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useStockStore } from '../../stores/stock.js'
import { scoreColor, decisionBadge } from '../../utils/stock.js'
import DividerLine from '../../components/DividerLine.vue'
import { marked } from 'marked'

const router = useRouter()
const store = useStockStore()
const stockCode = ref('')
const currentTab = ref('market')

/* 动态日期（YYYY.MM.DD 格式） */
const todayStr = computed(() => {
  const d = new Date()
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')}`
})

/* ── SSE 报告控制器（用于取消） ── */
let sseController = null

/* ── SSE 进度文案（computed 确保 current 变化时自动更新） ── */
const progressText = computed(() => {
  if (!store.sseGenerating) return ''
  const { current, total } = store.sseProgress
  return `正在采集数据... ${current}/${total} 维度`
})

/* ── Markdown 渲染（完整） ── */
const mdHtml = computed(() => {
  if (!store.sseReportMd) return ''
  return marked.parse(store.sseReportMd)
})

/* ── 公司画像（仅 module_2：公司画像与估值定位） ── */
function extractCompanyProfile(md) {
  if (!md) return ''
  /* 截取 "## 二、公司画像与估值定位" → 下一个模块前的内容 */
  const match = md.match(/## 二、公司画像与估值定位\n\n([\s\S]*?)(?=\n\n---\n\n## 三|$)/)
  return match ? match[1] : ''
}

const companyProfileMd = computed(() => extractCompanyProfile(store.sseReportMd))

const companyProfileHtml = computed(() => {
  if (!companyProfileMd.value) return ''
  return marked.parse(companyProfileMd.value)
})

const hasProfileContent = computed(() => !!companyProfileMd.value)

/* SSE 进度百分比 */
const ssePct = computed(() => {
  const { current, total } = store.sseProgress
  return total > 0 ? Math.round((current / total) * 100) : 0
})

/* 当前进行中的维度标签 */
const currentStageLabel = computed(() => {
  const stages = store.sseProgress.stages || []
  const running = stages.find(s => s.status === 'running')
  return running ? running.label : '...'
})

/* ── 10 维度 Tab 定义（与后端 DIMENSIONS 对齐） ── */
onMounted(() => {
  store.restoreCachedProfile()
  store.fetchWatchlist()
  store.fetchDashboardReports()
})

/* ── 输入校验 ── */
function validateCode() {
  const code = stockCode.value.trim()
  if (!code) { store.showToast('请输入股票代码'); return null }
  return code
}

/* ── 投研报告（取数 + DeepSeek 分析） ── */
function handleInvestReport() {
  if (sseController) sseController.abort()  // 取消上一次 SSE 连接
  const code = validateCode()
  if (!code) return
  sseController = store.triggerInvestReport(code)
}

/* ── 异步分析（兼容旧逻辑） ── */
async function handleAnalyze() {
  const code = stockCode.value.trim()
  if (!code) {
    store.showToast('请输入股票代码')
    return
  }
  await store.triggerAnalyze(code)
}

/* ── 导航 ── */
function goReport(id) {
  if (!id) return
  router.push(`/agent/stock/report/${id}`)
}

function goHistory() {
  router.push('/agent/stock/history')
}

/* ── 自选股轮播 ── */
const VISIBLE = 3
const currentSlide = ref(0)
const maxSlide = computed(() => Math.max(0, store.watchlist.length - VISIBLE))
const needsNav = computed(() => store.watchlist.length > VISIBLE)

/* 原型 dots 逻辑：≤3 页 → 1 枚，≥4 页 → 2 枚；点击时 toggle 跳转 */
const dotCount = computed(() => maxSlide.value <= 3 ? 1 : 2)
function goDot(idx) {
  if (dotCount.value === 1) {
    currentSlide.value = currentSlide.value === 0 ? maxSlide.value : 0
  } else {
    currentSlide.value = idx === 0 ? 0 : maxSlide.value
  }
}
/* 当前哪个 dot 应该高亮（原型逻辑：1 枚时仅 position 0 亮，2 枚时按前后半段分） */
const activeDot = computed(() => {
  if (dotCount.value === 1) return currentSlide.value === 0 ? 0 : -1
  return currentSlide.value < Math.ceil(maxSlide.value / 2) ? 0 : 1
})

function slidePrev() {
  if (currentSlide.value > 0) currentSlide.value--
}
function slideNext() {
  if (currentSlide.value < maxSlide.value) currentSlide.value++
}

/* 拖拽 */
const trackEl = ref(null)
const windowEl = ref(null)
let dragging = false, startX = 0, startTx = 0

function onPointerDown(e) {
  if (!needsNav.value) return
  dragging = true
  startX = e.clientX
  startTx = -currentSlide.value * (100 / VISIBLE)
}

function onPointerMove(e) {
  if (!dragging) return
  const dx = e.clientX - startX
  const w = windowEl.value?.offsetWidth || 1
  const tx = startTx + (dx / w) * 100
  if (trackEl.value) {
    trackEl.value.style.transition = 'none'
    trackEl.value.style.transform = `translateX(${tx}%)`
  }
}

function onPointerUp(e) {
  if (!dragging) return
  dragging = false
  const dx = e.clientX - startX
  const w = windowEl.value?.offsetWidth || 1
  if (trackEl.value) trackEl.value.style.transition = 'transform 0.45s cubic-bezier(0.16, 1, 0.3, 1)'
  if (dx < -w * 0.15) slideNext()
  else if (dx > w * 0.15) slidePrev()
  else {
    /* 回弹 */
    if (trackEl.value) trackEl.value.style.transform = `translateX(-${currentSlide.value * (100 / VISIBLE)}%)`
  }
}

</script>

<template>
  <div class="dashboard">
    <!-- ═══ 头版搜索区 ═══ -->
    <header class="masthead">
      <div class="masthead-title">
        <span class="issue-tag">MARKET INTELLIGENCE · {{ todayStr }}</span>
        <h1>股票分析台</h1>
        <p>输入股票代码，获取基于 iFind 数据的多维度市场简报</p>
      </div>
      <div class="search-desk" :class="{ running: store.sseGenerating || store.analyzing }">
        <span class="search-label">CODE</span>
        <input
          v-model="stockCode"
          type="text"
          placeholder="600519 / 贵州茅台"
          :disabled="store.sseGenerating || store.analyzing"
          @keyup.enter="handleInvestReport"
        />
        <button
          class="btn btn-report"
          :disabled="store.sseGenerating || store.analyzing"
          @click="handleInvestReport"
        >
          <span v-if="store.sseGenerating && store.sseReportMode === 'invest'" class="spinner-sm"></span>
          {{ store.sseGenerating && store.sseReportMode === 'invest' ? '分析中' : '投研报告' }}
        </button>
      </div>
    </header>

    <!-- SSE 进度条 -->
    <div class="progress-line" v-if="store.sseGenerating">
      <span class="spinner-sm"></span>
      <span>{{ progressText }}</span>
      <span class="progress-stage-label">「{{ currentStageLabel }}」</span>
      <!-- 维度进度圆点 -->
      <div class="progress-dots">
        <span
          v-for="s in store.sseProgress.stages"
          :key="s.stage"
          class="progress-dot"
          :class="{
            'dot-done': s.status === 'done',
            'dot-running': s.status === 'running',
            'dot-error': s.status === 'error',
          }"
          :title="s.label + (s.error ? '：' + s.error : '')"
        ></span>
      </div>
      <span class="progress-pct">{{ ssePct }}%</span>
    </div>

    <!-- 进度条（旧分析模式兼容） -->
    <div class="progress-line" v-if="store.analyzing && !store.sseGenerating">
      <span class="spinner-sm"></span>
      <span>正在调用 AI 分析引擎，请耐心等待...</span>
    </div>

    <!-- 投研报告结果区：仅展示公司画像与估值定位 -->
    <div class="card" v-if="store.sseReportMode === 'invest' && hasProfileContent && !store.sseGenerating" style="margin-bottom:24px;">
      <!-- 评分摘要行 -->
      <div v-if="store.analyzeResult" style="margin-bottom:16px;">
        <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
          <span style="font-size:1.5rem;font-weight:700;" :style="{color: scoreColor(store.analyzeResult.report?.score)}">
            {{ store.analyzeResult.report?.score }} 分
          </span>
          <span class="tag active">{{ decisionBadge(store.analyzeResult.report?.decision) }}</span>
        </div>
      </div>
      <!-- 公司画像与估值定位（仅 module_2） -->
      <div class="company-profile-section">
        <h3 style="font-size:1rem;margin:0 0 12px;">公司画像与估值定位</h3>
        <div class="markdown-body" v-html="companyProfileHtml"></div>
      </div>
      <!-- 右下角按钮 -->
      <div style="display:flex;justify-content:flex-end;margin-top:20px;">
        <button
          v-if="store.sseReportId"
          class="btn btn-report"
          @click="goReport(store.sseReportId)"
        >查看投研报告 →</button>
      </div>
    </div>

    <!-- 默认占位：无缓存且未生成报告时显示引导 -->
    <div class="card" v-if="!hasProfileContent && !store.sseGenerating" style="margin-bottom:24px;">
      <div class="empty-state" style="padding:40px;text-align:center;">
        <p style="color:var(--text-secondary);margin-bottom:8px;">输入股票代码，生成投研报告</p>
        <p style="color:var(--text-muted);font-size:0.85rem;">投研报告：iFind 数据采集 → DeepSeek AI 综合分析</p>
      </div>
    </div>

    <!-- ═══ 自选股 ═══ -->
    <section class="watchlist-bottom">
      <div class="watchlist-bottom-header">
        <h3>我的自选股</h3>
      </div>
      <div class="watchlist-carousel-window" ref="windowEl"
        @pointerdown="onPointerDown" @pointermove="onPointerMove" @pointerup="onPointerUp" @pointerleave="onPointerUp">
        <div class="watchlist-track" ref="trackEl" :style="{ transform: `translateX(-${currentSlide * (100 / VISIBLE)}%)` }">
          <div
            v-for="(item, idx) in store.watchlist"
            :key="item.stock_code"
            class="watchlist-col"
          >
            <DividerLine v-if="idx > 0" vertical />
            <div class="watchlist-code">{{ item.stock_code }}</div>
            <div class="watchlist-name">{{ item.stock_name || item.stock_code }}</div>
            <div class="watchlist-price">—</div>
            <span class="watchlist-change">—</span>
            <button class="watchlist-analyze-btn" @click="stockCode = item.stock_code; handleInvestReport()">投研报告</button>
          </div>
        </div>
      </div>
      <div class="watchlist-nav">
        <button class="watchlist-arrow" :disabled="currentSlide === 0" @click="slidePrev">
          <span>&#8249;</span>
        </button>
        <div class="watchlist-dots">
          <span
            v-for="(_, i) in dotCount"
            :key="i"
            class="watchlist-dot"
            :class="{ active: activeDot === i }"
            @click="goDot(i)"
          ></span>
        </div>
        <button class="watchlist-arrow" :disabled="currentSlide === maxSlide" @click="slideNext">
          <span>&#8250;</span>
        </button>
      </div>
    </section>

    <!-- ═══ 最近分析报告 ═══ -->
    <section v-if="store.dashboardReports.length > 0" class="reports-section">
      <div class="reports-container">
        <h2 class="reports-title">最近分析报告</h2>
        <div class="reports-steps">
          <div v-for="(r, idx) in store.dashboardReports" :key="r.id">
            <DividerLine v-if="idx > 0" />
            <div
              class="reports-step"
              @click="goReport(r.id)"
              style="cursor: pointer;"
            >
              <div class="reports-step-left">
                <svg class="reports-step-icon" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="10" stroke="#1a1a1a" stroke-width="1.5"/>
                  <path d="M8 12 L11 15 L16 9" stroke="#1a1a1a" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <span class="reports-step-title">{{ r.stock_name }} · {{ r.stock_code }} · <span :style="{ color: scoreColor(r.score) }">{{ r.score }} 分</span></span>
              </div>
              <p class="reports-step-desc">{{ decisionBadge(r.decision) }} · {{ r.created_at?.slice(0, 16) }}</p>
            </div>
          </div>
        </div>
        <a class="side-link" @click.prevent="goHistory" href="#" style="display:block;text-align:center;margin-top:32px;">查看全部报告 →</a>
      </div>
    </section>
  </div>
</template>

<style scoped>
/* ═══════════════════════════════════════════════
   精密纸媒交易台 — Dashboard 方案 B
   方向：高端金融印刷品 + 实体交易台精密感
   记忆点：数据像印在厚纸上的油墨，按钮像实体按键
   ═══════════════════════════════════════════════ */

.dashboard {
  --paper-bg: #ffffff;
  --paper-card: #ffffff;
  --paper-muted: #f5f5f4;
  --ink-primary: #1a1816;
  --ink-secondary: #6b6560;
  --ink-tertiary: #9a948d;
  --ink-disabled: #c4beb6;
  --dash-accent: #b45309;
  --dash-accent-hover: #92400e;
  --dash-green: #166534;
  --dash-green-soft: #dcfce7;
  --dash-red: #991b1b;
  --dash-red-soft: #fee2e2;
  --dash-border: #e5e5e5;
  --dash-border-light: #d5cfc6;
  --dash-shadow-sm: 0 1px 2px rgba(26,24,22,0.04);
  --dash-shadow-md: 0 4px 12px rgba(26,24,22,0.06);
  --dash-shadow-btn: inset 0 1px 0 rgba(255,255,255,0.25), 0 1px 2px rgba(26,24,22,0.08);
  --dash-shadow-btn-active: inset 0 1px 2px rgba(26,24,22,0.15);
  --dash-radius-sm: 3px;
  --dash-radius-md: 5px;
  --dash-radius-lg: 8px;
  --dash-ease-out: cubic-bezier(0.16, 1, 0.3, 1);
}

.dashboard {
  max-width: 1400px;
  margin: 0 auto;
  padding: 8px 40px 60px;
  color: var(--ink-primary);
}

/* ── 头版搜索区 ── */
.masthead {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 40px;
  align-items: end;
  padding-bottom: 28px;
  border-bottom: 1px solid var(--dash-border);
  margin-bottom: 28px;
}
.masthead-title h1 {
  font-family: 'Noto Serif SC', 'STSong', 'SimSun', serif;
  font-size: 2.6rem;
  font-weight: 900;
  letter-spacing: -0.03em;
  line-height: 1.1;
  margin-bottom: 8px;
}
.masthead-title p {
  color: var(--ink-secondary);
  font-size: 0.9rem;
  font-weight: 500;
  letter-spacing: 0.02em;
}
.issue-tag {
  display: inline-block;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  background: var(--ink-primary);
  color: #fff;
  padding: 3px 8px;
  border-radius: var(--dash-radius-sm);
  margin-bottom: 12px;
  letter-spacing: 0.08em;
}

/* 搜索框 */
.search-desk {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--paper-card);
  border: 1px solid var(--dash-border);
  border-radius: var(--dash-radius-md);
  padding: 10px 12px;
  box-shadow: var(--dash-shadow-sm);
  min-width: 360px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.search-desk:focus-within {
  border-color: var(--dash-accent);
  box-shadow: 0 0 0 3px rgba(180,83,9,0.08), var(--dash-shadow-sm);
}
.search-desk.running {
  background: var(--paper-muted);
}
.search-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: var(--ink-tertiary);
  white-space: nowrap;
  letter-spacing: 0.05em;
}
.search-desk input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-family: 'JetBrains Mono', monospace;
  font-size: 1rem;
  color: var(--ink-primary);
}
.search-desk input::placeholder {
  color: var(--ink-tertiary);
}
.search-desk input:disabled {
  color: var(--ink-disabled);
}

/* 按钮 */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: var(--dash-radius-sm);
  font-size: 0.85rem;
  font-weight: 600;
  border: 1px solid transparent;
  cursor: pointer;
  transition: all 0.12s ease;
  font-family: inherit;
  white-space: nowrap;
}
.btn-primary {
  background: var(--dash-accent);
  color: #fff;
  box-shadow: var(--dash-shadow-btn);
}
.btn-primary:hover {
  background: var(--dash-accent-hover);
  transform: translateY(-1px);
}
.btn-primary:active {
  transform: translateY(0);
  box-shadow: var(--dash-shadow-btn-active);
}
.btn-primary:disabled {
  background: var(--paper-muted);
  color: var(--ink-tertiary);
  border-color: var(--dash-border);
  cursor: not-allowed;
  transform: none;
}
.btn-report {
  background: var(--dash-green);
  color: #fff;
  box-shadow: var(--dash-shadow-btn);
}
.btn-report:hover {
  background: #14532d;
  transform: translateY(-1px);
}

/* 进度条 */
.progress-line {
  margin-bottom: 10px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.82rem;
  color: var(--ink-secondary);
  min-height: 22px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.spinner-sm {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid var(--dash-border);
  border-top-color: var(--dash-accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── 三栏主布局 ── */
.desk-grid {
  display: grid;
  grid-template-columns: 180px 1fr;
  gap: 28px;
  align-items: start;
}

/* 左侧维度目录 */
.dimension-toc h3 {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--ink-tertiary);
  margin-bottom: 14px;
}
.toc-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.toc-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--dash-radius-md);
  cursor: pointer;
  transition: all 0.15s ease;
  border: 1px solid transparent;
}
.toc-item:hover {
  background: var(--paper-muted);
}
.toc-item.active {
  background: var(--paper-card);
  border-color: var(--dash-border);
  box-shadow: var(--dash-shadow-sm);
}
.toc-num {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  color: var(--ink-tertiary);
  min-width: 18px;
}
.toc-item.active .toc-num {
  color: var(--dash-accent);
}
.toc-label {
  font-size: 0.88rem;
  font-weight: 500;
}
.toc-status {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--dash-green);
  margin-left: auto;
}

/* 中间维度面板 */
.dimension-stage {
  background: var(--paper-card);
  border: 1px solid var(--dash-border);
  border-radius: var(--dash-radius-lg);
  min-height: 520px;
  box-shadow: var(--dash-shadow-sm);
  overflow: hidden;
}
.stage-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 22px 26px;
  border-bottom: 1px solid var(--dash-border-light);
}
.stage-title h2 {
  font-family: 'Noto Serif SC', 'STSong', 'SimSun', serif;
  font-size: 1.4rem;
  font-weight: 700;
  letter-spacing: -0.01em;
}
.stock-sub {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.78rem;
  color: var(--ink-tertiary);
  margin-top: 2px;
}
.stage-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 4px 10px;
  border-radius: var(--dash-radius-sm);
}
.badge-ok {
  background: var(--dash-green-soft);
  color: var(--dash-green);
}
.badge-missing {
  background: var(--dash-red-soft);
  color: var(--dash-red);
}
.stage-body {
  padding: 26px;
}

/* 数据网格 */
.metric-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1px;
  background: var(--dash-border-light);
  border: 1px solid var(--dash-border-light);
  border-radius: var(--dash-radius-sm);
  overflow: hidden;
}
.metric-cell {
  background: var(--paper-card);
  padding: 18px;
  transition: background 0.15s ease;
}
.metric-cell:hover {
  background: var(--paper-muted);
}
.metric-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--ink-tertiary);
  margin-bottom: 6px;
}
.metric-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: -0.02em;
}
.metric-value.up { color: var(--dash-green); }
.metric-value.down { color: var(--dash-red); }
.metric-unit {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--ink-tertiary);
}

/* 市场环境 — 指数卡片 */
.env-index-card {
  background: var(--paper-card);
  border: 1px solid var(--dash-border-light);
  border-radius: var(--dash-radius-sm);
  padding: 18px;
  margin-bottom: 14px;
}
.env-index-name {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.85rem;
  font-weight: 700;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--dash-border-light);
}
.env-index-code {
  font-weight: 400;
  color: var(--ink-tertiary);
  margin-left: 8px;
}

/* 财务分区 */
.finance-report-date {
  font-size: 0.85rem;
  color: var(--ink-secondary);
  margin-bottom: 16px;
  padding: 8px 12px;
  background: var(--paper-muted);
  border-radius: var(--dash-radius-sm);
  font-family: 'JetBrains Mono', monospace;
}
.finance-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}
.finance-block h4 {
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--ink-secondary);
  padding-bottom: 8px;
  border-bottom: 1px solid var(--dash-border);
  margin-bottom: 10px;
}
.finance-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 7px 0;
  font-size: 0.85rem;
  border-bottom: 1px dashed var(--dash-border-light);
}
.finance-row:last-child {
  border-bottom: none;
}
.finance-row .label {
  color: var(--ink-tertiary);
}
.finance-row .value {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600;
}

/* 新闻列表 */
.news-list {
  list-style: none;
}
.news-item {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 14px 0;
  border-bottom: 1px solid var(--dash-border-light);
  transition: background 0.15s ease;
}
.news-item:hover {
  background: var(--paper-muted);
  margin: 0 -12px;
  padding: 14px 12px;
  border-radius: var(--dash-radius-sm);
}
.news-title {
  font-size: 0.92rem;
  font-weight: 500;
  line-height: 1.5;
}

/* ── 底部自选股 ── */
.watchlist-bottom {
  margin-top: 28px;
  padding: 90px 0;
  border-top: 1px solid var(--dash-border);
}
.watchlist-bottom-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 40px;
  padding: 0 4px;
}
.watchlist-bottom-header h3 {
  font-size: 0.85rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--ink-secondary);
}
.watchlist-carousel-window {
  overflow: hidden;
  position: relative;
  cursor: grab;
}
.watchlist-carousel-window:active {
  cursor: grabbing;
}
.watchlist-track {
  display: flex;
  transition: transform 0.45s var(--dash-ease-out);
  will-change: transform;
}
.watchlist-col {
  flex: 0 0 calc(100% / 3);
  padding: 30px 50px 42px;
  position: relative;
  display: flex;
  flex-direction: column;
}
.watchlist-code {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--ink-tertiary);
  letter-spacing: 0.06em;
}
.watchlist-name {
  font-family: 'Noto Serif SC', 'STSong', 'SimSun', serif;
  font-size: 1.65rem;
  font-weight: 700;
  line-height: 1.3;
  margin-top: 15px;
  margin-bottom: 84px;
}
.watchlist-price {
  font-family: 'JetBrains Mono', monospace;
  font-size: 2rem;
  font-weight: 700;
  margin-bottom: 9px;
}
.watchlist-change {
  display: inline-block;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.85rem;
  font-weight: 600;
  padding: 5px 12px;
  border-radius: var(--dash-radius-sm);
  margin-bottom: 72px;
  align-self: flex-start;
}
.watchlist-analyze-btn {
  width: 100%;
  padding: 20px 0;
  background: #f3f4f6;
  color: var(--ink-secondary);
  border: none;
  border-radius: var(--dash-radius-sm);
  font-family: inherit;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  margin-top: auto;
  transition: background 0.15s ease, color 0.15s ease;
}
.watchlist-analyze-btn:hover {
  background: #e5e7eb;
  color: var(--ink-primary);
}
.watchlist-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 18px;
  margin-top: 48px;
}
.watchlist-nav.hidden {
  display: none;
}
.watchlist-arrow {
  width: 30px;
  height: 30px;
  border-radius: 10px;
  border: 1px solid #1a1816;
  background: transparent;
  color: var(--ink-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  transition: transform 0.2s var(--dash-ease-out);
  padding: 0;
}
.watchlist-arrow span {
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.2s var(--dash-ease-out);
}
.watchlist-arrow:hover {
  transform: scale(1.13);
  border-radius: 12px;
}
.watchlist-arrow:hover span {
  transform: scale(0.885);
}
.watchlist-arrow:disabled {
  opacity: 0.28;
  cursor: not-allowed;
  transform: none !important;
}
.watchlist-arrow:disabled:hover span {
  transform: none !important;
}
.watchlist-dots {
  display: flex;
  align-items: center;
  gap: 10px;
}
.watchlist-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #d1d5db;
  cursor: pointer;
  transition: background 0.2s ease;
}
.watchlist-dot.active {
  background: #1a1816;
}

/* ── 最近报告 ── */
.reports-section {
  background: #fff;
  padding: 110px 0;
  border-top: 1px solid var(--dash-border);
}
.reports-container {
  max-width: 760px;
  margin: 0 auto;
  padding: 0 24px;
}
.reports-title {
  font-family: 'Noto Serif SC', 'STSong', 'SimSun', serif;
  font-size: 2.6rem;
  font-weight: 500;
  color: #111;
  text-align: center;
  margin-bottom: 72px;
  letter-spacing: -0.02em;
}
.reports-steps {
  display: flex;
  flex-direction: column;
}
.reports-step {
  display: flex;
  align-items: flex-start;
  gap: 0;
  padding: 52px 0;
  cursor: pointer;
  transition: background 0.15s ease;
}
.reports-step:hover {
  background: var(--paper-muted);
  margin: 0 -12px;
  padding: 52px 12px;
  border-radius: var(--dash-radius-sm);
}
.reports-step-left {
  width: 38%;
  flex-shrink: 0;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding-right: 28px;
}
.reports-step-icon {
  width: 22px;
  height: 22px;
  flex-shrink: 0;
  margin-top: 2px;
}
.reports-step-title {
  font-family: 'Noto Serif SC', 'STSong', 'SimSun', serif;
  font-size: 1.15rem;
  font-weight: 600;
  color: #111;
  line-height: 1.5;
}
.reports-step-desc {
  width: 62%;
  font-size: 0.93rem;
  font-weight: 400;
  color: #666;
  line-height: 1.65;
}
.side-link {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--dash-accent);
  text-decoration: none;
}
.side-link:hover {
  color: var(--dash-accent-hover);
}

/* 维度内容（信号标签 + 洞察文本） */
.dimension-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 信号标签 */
.signal-tag {
  display: inline-block;
  align-self: flex-start;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 4px 12px;
  border-radius: var(--dash-radius-sm);
}
.signal-positive {
  background: var(--dash-green-soft);
  color: var(--dash-green);
}
.signal-neutral {
  background: #fef3c7;
  color: #92400e;
}
.signal-negative {
  background: var(--dash-red-soft);
  color: var(--dash-red);
}

/* 洞察文本 */
.dimension-insight {
  font-size: 0.92rem;
  line-height: 1.85;
  color: var(--ink-primary);
  white-space: pre-wrap;
}

/* 消息面主题标签 */
.key-themes {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.theme-chip {
  display: inline-block;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.68rem;
  color: var(--ink-secondary);
  background: var(--paper-muted);
  padding: 4px 10px;
  border-radius: var(--dash-radius-sm);
  border: 1px solid var(--dash-border-light);
}

/* 风险列表 */
.risk-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.risk-item {
  font-size: 0.88rem;
  color: var(--dash-red);
  background: var(--dash-red-soft);
  padding: 10px 14px;
  border-radius: var(--dash-radius-sm);
  border-left: 3px solid var(--dash-red);
  line-height: 1.5;
}

/* 维度切换动画 */
.stage-panel {
  animation: fadeIn 0.35s var(--dash-ease-out);
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateX(8px); }
  to { opacity: 1; transform: translateX(0); }
}

/* 响应式 */
@media (max-width: 1100px) {
  .desk-grid {
    grid-template-columns: 160px 1fr;
  }
}
@media (max-width: 820px) {
  .masthead {
    grid-template-columns: 1fr;
  }
  .search-desk {
    min-width: auto;
  }
  .desk-grid {
    grid-template-columns: 1fr;
  }
  .dimension-toc {
    position: static;
    display: flex;
    gap: 8px;
    overflow-x: auto;
  }
  .toc-list {
    flex-direction: row;
  }
  .toc-item {
    white-space: nowrap;
  }
  .metric-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .watchlist-col {
    flex: 0 0 100%;
    padding: 30px 20px;
  }
  .watchlist-col + .watchlist-col {
    border-top: 1px solid var(--dash-border-light);
    padding-top: 30px;
    margin-top: 10px;
  }
  .reports-section {
    padding: 64px 0;
  }
  .reports-title {
    font-size: 2rem;
    margin-bottom: 48px;
  }
  .reports-step {
    flex-direction: column;
    gap: 14px;
    padding: 36px 0;
  }
  .reports-step-left,
  .reports-step-desc {
    width: 100%;
    padding-right: 0;
  }
}

/* ── SSE 进度圆点 ── */
.progress-stage-label {
  color: var(--dash-accent);
  font-weight: 600;
}
.progress-dots {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0 4px;
}
.progress-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--dash-border-light);
  transition: all 0.25s ease;
}
.progress-dot.dot-done {
  background: var(--dash-green);
}
.progress-dot.dot-running {
  background: var(--dash-accent);
  animation: dotPulse 0.8s ease infinite;
}
.progress-dot.dot-error {
  background: var(--dash-red);
}
@keyframes dotPulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.6); opacity: 0.5; }
}
.progress-pct {
  font-weight: 700;
  color: var(--dash-accent);
}

/* ── 报告布局：左侧 Tab + 右侧散文内容 ── */
.report-layout {
  display: grid;
  grid-template-columns: 200px 1fr;
  gap: 0;
  border: 1px solid var(--dash-border);
  border-radius: var(--dash-radius-lg);
  overflow: hidden;
  box-shadow: var(--dash-shadow-sm);
  background: var(--paper-card);
}

/* 左侧维度目录（覆盖默认 toc 样式） */
.report-layout .dimension-toc {
  border-right: 1px solid var(--dash-border-light);
  padding: 12px 0;
  background: var(--paper-muted);
}
.report-layout .dimension-toc .toc-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  cursor: pointer;
  transition: all 0.15s ease;
  border: none;
  border-radius: 0;
  border-left: 2px solid transparent;
}
.report-layout .dimension-toc .toc-item:hover {
  background: rgba(0,0,0,0.03);
}
.report-layout .dimension-toc .toc-item.active {
  background: var(--paper-card);
  border-left-color: var(--dash-accent);
  box-shadow: none;
}
.toc-icon {
  font-size: 1rem;
  width: 22px;
  text-align: center;
  flex-shrink: 0;
}
.toc-label {
  font-size: 0.83rem;
  font-weight: 500;
  color: var(--ink-secondary);
}
.toc-item.active .toc-label {
  color: var(--dash-accent);
  font-weight: 600;
}
.toc-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--dash-border-light);
  margin-left: auto;
  flex-shrink: 0;
}
.toc-dot-ok {
  background: var(--dash-green);
}
.toc-dot-err {
  background: var(--dash-red);
}

/* 右侧维度面板 */
.report-layout .dimension-stage {
  border: none;
  border-radius: 0;
  box-shadow: none;
  min-height: 440px;
  display: flex;
  flex-direction: column;
}
.stage-icon {
  font-size: 1.3rem;
  margin-right: 8px;
}
.stage-title {
  display: flex;
  align-items: center;
}
.stage-title h2 {
  font-family: 'Noto Serif SC', 'STSong', 'SimSun', serif;
  font-size: 1.2rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  margin: 0;
}
.stage-body {
  flex: 1;
  padding: 24px 28px;
  overflow-y: auto;
}

/* 散文内容区域 */
.dimension-prose {
  font-family: 'Noto Serif SC', 'STSong', 'SimSun', serif;
  color: var(--ink-primary);
  line-height: 1.9;
}

/* 响应式：报告布局 */
@media (max-width: 820px) {
  .report-layout {
    grid-template-columns: 1fr;
  }
  .report-layout .dimension-toc {
    display: flex;
    overflow-x: auto;
    border-right: none;
    border-bottom: 1px solid var(--dash-border-light);
    padding: 8px;
  }
  .report-layout .dimension-toc .toc-item {
    white-space: nowrap;
    padding: 8px 12px;
    border-left: none;
    border-bottom: 2px solid transparent;
  }
  .report-layout .dimension-toc .toc-item.active {
    border-left-color: transparent;
    border-bottom-color: var(--dash-accent);
  }
}

/* ── Markdown 报告内容样式 ── */
.markdown-body { line-height: 1.8; color: var(--text-secondary, #6b6560); }
.markdown-body h1 { font-size: 1.5rem; margin: 24px 0 12px; color: var(--text-primary, #1a1816); border-bottom: 1px solid var(--dash-border); padding-bottom: 8px; }
.markdown-body h2 { font-size: 1.3rem; margin: 24px 0 12px; color: var(--text-primary, #1a1816); }
.markdown-body h3 { font-size: 1.1rem; margin: 20px 0 10px; color: var(--text-primary, #1a1816); }
.markdown-body h4 { font-size: 1rem; margin: 16px 0 8px; color: var(--text-primary, #1a1816); }
.markdown-body p { margin: 8px 0; }
.markdown-body blockquote {
  margin: 12px 0;
  padding: 12px 16px;
  background: var(--paper-muted, #f5f5f4);
  border-left: 3px solid var(--dash-accent);
  border-radius: 0 var(--dash-radius-sm) var(--dash-radius-sm) 0;
}
.markdown-body li { margin: 4px 0 4px 20px; }
.markdown-body code {
  background: var(--bg-hover, #f5f5f4);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.85em;
  color: var(--dash-accent);
}
.markdown-body hr { border: none; border-top: 1px solid var(--dash-border-light); margin: 24px 0; }
.markdown-body strong { color: var(--text-primary, #1a1816); }
.markdown-body table { width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 0.9rem; }
.markdown-body th, .markdown-body td { padding: 10px 14px; border: 1px solid var(--dash-border-light); text-align: left; }
.markdown-body th { background: var(--paper-muted, #f5f5f4); font-weight: 700; }
.markdown-body tr:hover { background: var(--paper-muted, #f5f5f4); }
</style>
