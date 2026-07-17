import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    console.error('[API] Error:', err.message)
    return Promise.reject(err)
  }
)

/* ── 仪表盘 ── */
export const getDashboardStats = () => api.get('/dashboard/stats')

/* ── 内容预览 ── */
export const getTrends = (params) => api.get('/preview/trends', { params })
export const getNews = (params) => api.get('/preview/news', { params })
export const getAvailableDates = () => api.get('/preview/dates')

/* ── 推送历史 ── */
export const getHistory = (limit = 30) => api.get('/history/list', { params: { limit } })
export const getHistoryDetail = (id) => api.get(`/history/detail/${id}`)

/* ── 手动触发 ── */
export const triggerFetch = () => api.post('/trigger/fetch')
export const triggerPush = () => api.post('/trigger/push')
export const triggerFull = () => api.post('/trigger/full')
export const getTaskResult = (taskId) => api.get(`/trigger/result/${taskId}`)

/* ── 关键词配置 ── */
export const getKeywords = () => api.get('/config/keywords')
export const addKeyword = (data) => api.post('/config/keywords', data)
export const updateKeyword = (keyword, data) => api.put(`/config/keywords/${keyword}`, data)
export const deleteKeyword = (keyword) => api.delete(`/config/keywords/${keyword}`)

/* ── 飞书 Webhook ── */
export const getWebhook = () => api.get('/config/webhook')
export const updateWebhook = (url) => api.put('/config/webhook', { url })

/* ── 健康检查 ── */
export const healthCheck = () => api.get('/health')

/* ═══════════════════════════════════════════
 * 股票分析
 * ═══════════════════════════════════════════ */
export const triggerStockAnalyze = (stockCode) =>
  api.post('/stock/analyze', { stock_code: stockCode })

export const getStockAnalyzeResult = (taskId) =>
  api.get(`/stock/analyze/result/${taskId}`)

/* 原始数据采集（不调 LLM） */
export const triggerStockCollect = (stockCode) =>
  api.post('/stock/collect', { stock_code: stockCode })

export const getStockCollectResult = (taskId) =>
  api.get(`/stock/collect/result/${taskId}`)

export const getStockReports = (params) =>
  api.get('/stock/reports', { params })

export const getStockReportDetail = (id) =>
  api.get(`/stock/reports/${id}`)

export const getStockWatchlist = () =>
  api.get('/stock/watchlist')

export const addStockWatchlist = (data) =>
  api.post('/stock/watchlist', data)

export const deleteStockWatchlist = (stockCode) =>
  api.delete(`/stock/watchlist/${stockCode}`)

export const updateStockWatchlist = (stockCode, data) =>
  api.put(`/stock/watchlist/${stockCode}`, data)

export const triggerWatchlistAnalyze = () =>
  api.post('/stock/trigger/market-report')

export const pushStockReport = (id) =>
  api.post(`/stock/reports/${id}/push`)

/* ═══════════════════════════════════════════
 * SKILL 驱动的 SSE 报告（新架构）
 * ═══════════════════════════════════════════ */

/**
 * SSE 数据报告：10 维度采集 → 流式推送 Markdown
 *
 * @param {string} stockCode
 * @param {object} callbacks
 * @param {function} callbacks.onProgress  ({ stage, label, status, current, total, error? })
 * @param {function} callbacks.onComplete  ({ report, has_critical_failure })
 * @param {function} callbacks.onError     (error)
 * @returns {AbortController} 用于取消请求
 */
export function fetchSkillReport(stockCode, { onProgress, onComplete, onError } = {}, dimensions = null) {
  const controller = new AbortController()
  const body = { stock_code: stockCode }
  if (dimensions && dimensions.length) body.dimensions = dimensions

  fetch('/api/stock/skill-report', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: controller.signal,
  }).then(async (res) => {
    if (!res.ok) {
      onError?.(new Error(`HTTP ${res.status}`))
      return
    }
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      // 解析 SSE 消息（以 \n\n 分隔）
      const parts = buffer.split('\n\n')
      buffer = parts.pop()  // 最后一个可能未完成

      for (const part of parts) {
        const line = part.trim()
        if (!line.startsWith('data: ')) continue
        try {
          const data = JSON.parse(line.slice(6))
          if (data.type === 'progress') {
            onProgress?.(data)
          } else if (data.type === 'complete') {
            onComplete?.(data)
          } else if (data.type === 'error') {
            onError?.(new Error(data.message || '未知错误'))
          }
        } catch (_) { /* 解析失败跳过 */ }
      }
    }
  }).catch(err => {
    if (err.name !== 'AbortError') onError?.(err)
  })

  return controller
}

/**
 * SSE 投研报告：数据采集 → DeepSeek 分析 → 流式推送
 * 回调签名与 fetchSkillReport 一致，但 complete 事件多出 { score, decision, usage }
 */
export function fetchInvestReport(stockCode, { onProgress, onComplete, onError } = {}, dimensions = null) {
  const controller = new AbortController()
  const body = { stock_code: stockCode }
  if (dimensions && dimensions.length) body.dimensions = dimensions

  fetch('/api/stock/skill-report/invest', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: controller.signal,
  }).then(async (res) => {
    if (!res.ok) {
      onError?.(new Error(`HTTP ${res.status}`))
      return
    }
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      const parts = buffer.split('\n\n')
      buffer = parts.pop()

      for (const part of parts) {
        const line = part.trim()
        if (!line.startsWith('data: ')) continue
        try {
          const data = JSON.parse(line.slice(6))
          if (data.type === 'progress') {
            onProgress?.(data)
          } else if (data.type === 'llm_start') {
            onProgress?.({ stage: 'llm', label: 'DeepSeek 分析', status: 'running' })
          } else if (data.type === 'complete') {
            onComplete?.(data)
          } else if (data.type === 'error') {
            onError?.(new Error(data.message || '未知错误'))
          }
        } catch (_) { /* 解析失败跳过 */ }
      }
    }
  }).catch(err => {
    if (err.name !== 'AbortError') onError?.(err)
  })

  return controller
}
