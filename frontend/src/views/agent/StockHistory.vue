<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useStockStore } from '../../stores/stock.js'

const router = useRouter()
const store = useStockStore()

/* ── 筛选状态 ── */
const filters = reactive({
  search: '',
  dateFrom: '',
  dateTo: '',
  decision: '',
})

const page = ref(1)
const pageSize = 8

/* ── 搜索防抖 ── */
let debounceTimer = null
function onSearchInput() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => applyFilter(), 300)
}

/* ── 数据加载 ── */
function loadData() {
  store.fetchHistoryReports(page.value, pageSize, { ...filters })
}

function applyFilter() {
  page.value = 1
  loadData()
}

function clearFilters() {
  filters.search = ''
  filters.dateFrom = ''
  filters.dateTo = ''
  filters.decision = ''
  page.value = 1
  loadData()
}

function goToPage(p) {
  if (p === page.value) return
  page.value = p
  loadData()
}

/* ── 总页数 ── */
const totalPages = computed(() =>
  Math.max(1, Math.ceil(store.historyReportsTotal / pageSize))
)

/* ── 页码截断（页数多时用省略号，参考 Figma Pagination 77:2197） ── */
const pageItems = computed(() => {
  const total = totalPages.value
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)
  const set = new Set([1, 2, 3, total - 1, total, page.value - 1, page.value, page.value + 1])
  const arr = [...set].filter(p => p >= 1 && p <= total).sort((a, b) => a - b)
  const result = []
  let prev = 0
  for (const p of arr) {
    if (p - prev > 1) result.push('…')
    result.push(p)
    prev = p
  }
  return result
})

/* ── 导航 ── */
function goReport(id) {
  if (!id) return
  router.push(`/agent/stock/report/${id}`)
}

/* ── 评分颜色等级 ── */
function scoreClass(score) {
  if (score >= 70) return 'high'
  if (score >= 45) return 'mid'
  return 'low'
}

/* ── 判断标签映射 ── */
function verdictClass(decision) {
  if (!decision) return 'neutral'
  if (decision.includes('看多')) return 'bullish'
  if (decision.includes('看空')) return 'bearish'
  return 'neutral'
}

function verdictText(decision) {
  if (!decision) return '—'
  if (decision.includes('看多')) return '看多'
  if (decision.includes('看空')) return '看空'
  if (decision.includes('震荡')) return '震荡'
  return decision
}

/* ── 日期格式化 ── */
function formatDate(dt) {
  if (!dt) return ''
  return dt.slice(0, 10)
}
function formatTime(dt) {
  if (!dt) return ''
  return dt.slice(11, 16)
}

onMounted(() => { loadData() })
onUnmounted(() => { clearTimeout(debounceTimer) })
</script>

<template>
  <div class="history-page">
    <!-- ═══ 页面头版 ═══ -->
    <header class="masthead">
      <div class="masthead-title">
        <span class="issue-tag">ARCHIVE · REPORT INDEX</span>
        <h1>历史报告</h1>
        <p>浏览和管理已生成的所有股票分析报告</p>
      </div>
    </header>

    <!-- ═══ 筛选栏 ═══ -->
    <div class="filter-bar">
      <span class="filter-label">搜索</span>
      <input
        class="filter-input"
        type="text"
        v-model="filters.search"
        @input="onSearchInput"
        placeholder="股票代码或名称…"
      >
      <span class="filter-label">日期</span>
      <input
        class="filter-input"
        type="date"
        v-model="filters.dateFrom"
        @change="applyFilter"
        style="min-width:140px"
      >
      <span class="filter-sep">至</span>
      <input
        class="filter-input"
        type="date"
        v-model="filters.dateTo"
        @change="applyFilter"
        style="min-width:140px"
      >
      <span class="filter-label">判断</span>
      <select
        class="filter-select"
        v-model="filters.decision"
        @change="applyFilter"
      >
        <option value="">全部</option>
        <option value="看多">看多</option>
        <option value="震荡">震荡</option>
        <option value="看空">看空</option>
      </select>
      <button class="filter-clear" @click="clearFilters">清除筛选</button>
    </div>

    <!-- ═══ 加载中 ═══ -->
    <div v-if="store.loading" class="loading-box">
      <span class="spinner"></span> 加载中...
    </div>

    <template v-else>
      <!-- ═══ 结果计数 ═══ -->
      <div class="result-count">共 {{ store.historyReportsTotal }} 条报告</div>

      <!-- ═══ 空状态 ═══ -->
      <div v-if="store.historyReports.length === 0" class="empty-state">
        <h4>没有匹配的报告</h4>
        <p>尝试调整筛选条件</p>
      </div>

      <!-- ═══ 报告列表 ═══ -->
      <template v-else>
        <div class="report-list">
          <!-- 列表头 -->
          <div class="report-row header-row">
            <span class="report-col-header">股票代码</span>
            <span class="report-col-header">股票名称</span>
            <span class="report-col-header">综合评分</span>
            <span class="report-col-header">判断</span>
            <span class="report-col-header">日期时间</span>
            <span class="report-col-header">操作</span>
          </div>
          <!-- 数据行 -->
          <div
            v-for="r in store.historyReports"
            :key="r.id"
            class="report-row"
          >
            <span class="report-code">{{ r.stock_code }}</span>
            <span class="report-name">{{ r.stock_name }}</span>
            <div class="score-cell">
              <span class="score-num" :class="scoreClass(r.score)">{{ r.score }}</span>
              <div class="score-bar">
                <div
                  class="score-bar-fill"
                  :class="scoreClass(r.score)"
                  :style="{ width: (r.score || 0) + '%' }"
                ></div>
              </div>
            </div>
            <span>
              <span class="verdict-tag" :class="verdictClass(r.decision)">
                {{ verdictText(r.decision) }}
              </span>
            </span>
            <span class="report-time">
              {{ formatDate(r.created_at) }}<br>
              <span class="report-time-sub">{{ formatTime(r.created_at) }}</span>
            </span>
            <div class="action-btns">
              <button class="btn-icon" title="查看报告" @click="goReport(r.id)">▶</button>
              <button class="btn-icon" title="推送到飞书" @click="store.pushToFeishu(r.id)">↗</button>
            </div>
          </div>
        </div>

        <!-- ═══ 分页 ═══ -->
        <div v-if="store.historyReportsTotal > pageSize" class="pagination">
          <button
            class="page-arrow"
            :disabled="page <= 1"
            @click="goToPage(page - 1)"
            aria-label="上一页"
          >
            <svg viewBox="0 0 9.33 9.33" width="9" height="9" fill="none"><path d="M4.67 9.33 L0 4.67 L4.67 0" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>
            <span>Previous</span>
          </button>
          <div class="page-nums">
            <template v-for="(item, i) in pageItems">
              <span v-if="item === '…'" :key="'gap' + i" class="page-gap">…</span>
              <button
                v-else
                :key="'num' + i"
                class="page-num"
                :class="{ active: item === page }"
                @click="goToPage(item)"
              >{{ item }}</button>
            </template>
          </div>
          <button
            class="page-arrow"
            :disabled="page >= totalPages"
            @click="goToPage(page + 1)"
            aria-label="下一页"
          >
            <span>Next</span>
            <svg viewBox="0 0 9.33 9.33" width="9" height="9" fill="none"><path d="M4.67 0 L9.33 4.67 L4.67 9.33" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </button>
        </div>
      </template>
    </template>
  </div>
</template>

<style scoped>
/* ═══════════════════════════════════════════════
   历史报告 — 精密纸媒交易台
   方向：高端金融印刷品 + 实体交易台精密感
   与 Dashboard 共享设计系统
   ═══════════════════════════════════════════════ */

.history-page {
  --paper-bg: #ffffff;
  --paper-card: #ffffff;
  --paper-muted: #f5f5f4;
  --ink-primary: #1a1816;
  --ink-secondary: #6b6560;
  --ink-tertiary: #9a948d;
  --ink-disabled: #c4beb6;
  --accent: #b45309;
  --accent-hover: #92400e;
  --accent-soft: #fef3c7;
  --accent-ink: #78350f;
  --green: #166534;
  --green-soft: #dcfce7;
  --red: #991b1b;
  --red-soft: #fee2e2;
  --border: #e5e5e5;
  --border-light: #e8e8e8;
  --shadow-sm: 0 1px 2px rgba(26,24,22,0.04);
  --shadow-md: 0 4px 12px rgba(26,24,22,0.06);
  --shadow-btn: inset 0 1px 0 rgba(255,255,255,0.25), 0 1px 2px rgba(26,24,22,0.08);
  --shadow-btn-active: inset 0 1px 2px rgba(26,24,22,0.15);
  --radius-sm: 3px;
  --radius-md: 5px;
  --radius-lg: 8px;
}

.history-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 32px 40px 60px;
  color: var(--ink-primary);
}

/* ── 页面头版 ── */
.masthead {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  padding-bottom: 28px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 28px;
}
.masthead-title .issue-tag {
  display: inline-block;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  background: var(--ink-primary);
  color: var(--paper-card);
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  margin-bottom: 12px;
  letter-spacing: 0.08em;
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

/* ── 筛选栏 ── */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 32px;
}
.filter-bar .filter-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--ink-tertiary);
  margin-right: 4px;
}
.filter-sep {
  color: var(--ink-tertiary);
  font-size: 0.8rem;
}
.filter-input {
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  font-size: 0.82rem;
  font-family: 'JetBrains Mono', monospace;
  color: var(--ink-primary);
  background: var(--paper-card);
  outline: none;
  min-width: 180px;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.filter-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(180,83,9,0.08);
}
.filter-input::placeholder {
  color: var(--ink-tertiary);
}
.filter-select {
  padding: 8px 32px 8px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  font-size: 0.82rem;
  font-family: 'JetBrains Mono', monospace;
  color: var(--ink-primary);
  background: var(--paper-card);
  outline: none;
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6' fill='%239a948d'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 10px center;
  transition: border-color 0.15s ease;
}
.filter-select:focus {
  border-color: var(--accent);
}
.filter-clear {
  font-size: 0.78rem;
  color: var(--accent);
  cursor: pointer;
  background: none;
  border: none;
  font-family: 'Bricolage Grotesque', 'PingFang SC', sans-serif;
  font-weight: 500;
  margin-left: auto;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  transition: background 0.15s ease;
}
.filter-clear:hover {
  background: var(--accent-soft);
}

/* ── 结果计数 ── */
.result-count {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.72rem;
  color: var(--ink-tertiary);
  margin-bottom: 16px;
}

/* ── 报告列表 ── */
.report-list {
  border-top: 1px solid var(--border);
}
.report-row {
  display: grid;
  grid-template-columns: 100px 1fr 90px 72px 130px 80px;
  gap: 24px;
  align-items: center;
  padding: 18px 0;
  border-bottom: 1px solid var(--border-light);
  transition: background 0.15s ease;
}
.report-row:hover {
  background: var(--paper-muted);
  margin: 0 -12px;
  padding: 18px 12px;
  border-radius: var(--radius-sm);
}
.report-row.header-row {
  padding: 10px 0;
  border-bottom: 1px solid var(--ink-primary);
}
.report-row.header-row:hover {
  background: none;
  margin: 0;
  padding: 10px 0;
  border-radius: 0;
}
.report-col-header {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.68rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--ink-tertiary);
}

/* ── 报告行内容 ── */
.report-code {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--ink-primary);
}
.report-name {
  font-family: 'Noto Serif SC', 'STSong', 'SimSun', serif;
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--ink-primary);
}

/* 评分条 */
.score-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}
.score-num {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.15rem;
  font-weight: 700;
  min-width: 36px;
}
.score-num.high { color: var(--green); }
.score-num.mid { color: var(--ink-secondary); }
.score-num.low { color: var(--red); }
.score-bar {
  width: 56px;
  height: 3px;
  background: var(--border-light);
  border-radius: 2px;
  overflow: hidden;
}
.score-bar-fill {
  height: 100%;
  border-radius: 2px;
}
.score-bar-fill.high { background: var(--green); }
.score-bar-fill.mid { background: var(--ink-tertiary); }
.score-bar-fill.low { background: var(--red); }

/* 判断标签 */
.verdict-tag {
  display: inline-block;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  white-space: nowrap;
}
.verdict-tag.bullish { background: var(--green-soft); color: var(--green); }
.verdict-tag.neutral { background: var(--paper-muted); color: var(--ink-secondary); }
.verdict-tag.bearish { background: var(--red-soft); color: var(--red); }

/* 日期 */
.report-time {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.78rem;
  color: var(--ink-tertiary);
}
.report-time-sub {
  font-size: 0.7rem;
  color: var(--ink-tertiary);
}

/* 操作按钮 */
.action-btns {
  display: flex;
  gap: 6px;
}
.btn-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--paper-card);
  cursor: pointer;
  font-size: 13px;
  color: var(--ink-secondary);
  transition: all 0.15s ease;
  padding: 0;
}
.btn-icon:hover {
  background: var(--paper-muted);
  border-color: var(--ink-primary);
  color: var(--ink-primary);
}

/* ── 分页（参考 Figma Pagination 77:2197） ── */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 40px;
}
.page-arrow {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 32px;
  padding: 8px 12px;
  border: none;
  border-radius: 8px;
  background: transparent;
  font-family: 'Inter', sans-serif;
  font-size: 16px;
  line-height: 1;
  color: var(--ink-primary);
  cursor: pointer;
  transition: background 0.15s ease;
}
.page-arrow svg {
  flex-shrink: 0;
}
.page-arrow:hover {
  background: var(--paper-muted);
}
.page-arrow:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.page-arrow:disabled:hover {
  background: transparent;
}
.page-nums {
  display: flex;
  align-items: center;
  gap: 8px;
}
.page-num,
.page-gap {
  min-width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 8px;
  font-family: 'Inter', sans-serif;
  font-size: 16px;
  color: var(--ink-primary);
}
.page-num {
  border: none;
  border-radius: 8px;
  background: transparent;
  cursor: pointer;
  transition: background 0.15s ease;
}
.page-num:hover {
  background: var(--paper-muted);
}
.page-num.active {
  background: var(--ink-primary);
  color: var(--paper-card);
}
.page-num.active:hover {
  background: var(--ink-primary);
}

/* ── 空状态 ── */
.empty-state {
  text-align: center;
  padding: 80px 0;
}
.empty-state h4 {
  font-family: 'Noto Serif SC', 'STSong', 'SimSun', serif;
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--ink-secondary);
  margin-bottom: 6px;
}
.empty-state p {
  font-size: 0.85rem;
  color: var(--ink-tertiary);
}

/* ── 加载态 ── */
.loading-box {
  text-align: center;
  padding: 60px 20px;
  color: var(--ink-tertiary);
  font-size: 0.9rem;
}
.spinner {
  display: inline-block;
  width: 18px;
  height: 18px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  vertical-align: middle;
  margin-right: 8px;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── 响应式 ── */
@media (max-width: 900px) {
  .history-page {
    padding: 20px;
  }
  .report-row {
    grid-template-columns: 1fr;
    gap: 8px;
    padding: 20px 0;
  }
  .report-row.header-row {
    display: none;
  }
  .filter-bar {
    gap: 6px;
  }
  .filter-input {
    min-width: 120px;
  }
}
</style>
