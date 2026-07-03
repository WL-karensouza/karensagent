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
