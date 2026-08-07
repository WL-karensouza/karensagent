import { defineStore } from 'pinia'
import * as api from '../api/index.js'

/* localStorage 键名 — 公司画像缓存 */
const PROFILE_CACHE_KEY = 'stock_company_profile'

export const useStockStore = defineStore('stock', {
  state: () => ({
    /* 报告 — 按页面独立，避免互相污染 */
    dashboardReports: [],
    dashboardReportsTotal: 0,
    historyReports: [],
    historyReportsTotal: 0,
    currentReport: null,

    /* 自选股 */
    watchlist: [],
    watchlistReports: {},   // { code: { score, decision, created_at } | null }

    /* 分析状态 */
    analyzing: false,
    analyzeTaskId: null,
    analyzeResult: null,

    /* SSE 流式报告 */
    sseProgress: { current: 0, total: 10, stages: [] },
    sseGenerating: false,
    sseReportMd: '',
    sseReportMode: null,   // 'data' | 'invest'
    sseSections: {},       // { dim_key: prose_text, ... } 各维度散文
    sseReportId: null,     // 投研报告存库后的 ID，用于跳转详情

    /* 加载 */
    loading: false,
    reportLoading: false,
    reportError: null,

    /* 评分趋势 */
    trendPoints: [],

    /* AI 问答 */
    chatMessages: [],       // [{ role, content, tool_calls }]
    chatSession: null,      // { id, stock_code, ... }
    chatAsking: false,      // 是否正在请求
    chatThinking: false,    // 是否正在思考/查数
    chatToolSteps: [],      // [{ id, label, status }] 工具步骤卡片

    /* Toast */
    toast: null,
  }),

  actions: {
    showToast(message, duration = 3000) {
      this.toast = message
      setTimeout(() => { this.toast = null }, duration)
    },

    /* ── 分析 ── */
    async triggerAnalyze(stockCode) {
      this.analyzing = true
      this.analyzeResult = null
      try {
        const res = await api.triggerStockAnalyze(stockCode)
        if (res.code !== 0 || !res.task_id) {
          this.showToast(res.message || '触发分析失败')
          this.analyzing = false
          return
        }
        this.analyzeTaskId = res.task_id

        // 轮询结果：每 3s 一次，最多 80 次（240s，适配 deepseek-reasoner ~3min 推理时间）
        for (let i = 0; i < 80; i++) {
          await new Promise(r => setTimeout(r, 3000))
          try {
            const result = await api.getStockAnalyzeResult(this.analyzeTaskId)
            if (result.code !== 0) continue
            if (result.data.status === 'done') {
              this.analyzeResult = result.data
              this.showToast(result.data.message || '分析完成')
              await this.fetchDashboardReports()
              this.analyzing = false
              return
            }
            if (result.data.status === 'error') {
              this.showToast('分析失败: ' + result.data.message)
              this.analyzing = false
              return
            }
          } catch (e) {
            /* 单次轮询失败不中断 */
          }
        }
        this.showToast('分析超时，请稍后刷新查看')
      } catch (e) {
        this.showToast('分析失败: ' + (e.message || '网络错误'))
      } finally {
        this.analyzing = false
      }
    },

    /* ── SKILL 数据报告（SSE 流式，仅取数不分析） ── */
    triggerSkillReport(stockCode) {
      this._startSse('data')
      let dimensions = null
      try {
        const raw = localStorage.getItem('stock_settings_dimensions')
        if (raw) dimensions = JSON.parse(raw)
      } catch (_) {}
      return api.fetchSkillReport(stockCode, {
        onProgress: (data) => { this._onSseProgress(data) },
        onComplete: (data) => { this._onSseComplete('data', data) },
        onError: (err) => { this._onSseError(err) },
      }, dimensions)
    },

    /* ── SKILL 投研报告（SSE 流式，取数 + DeepSeek 分析） ── */
    triggerInvestReport(stockCode) {
      this._startSse('invest')
      let dimensions = null
      try {
        const raw = localStorage.getItem('stock_settings_dimensions')
        if (raw) dimensions = JSON.parse(raw)
      } catch (_) {}
      return api.fetchInvestReport(stockCode, {
        onProgress: (data) => { this._onSseProgress(data) },
        onComplete: (data) => { this._onSseComplete('invest', data) },
        onError: (err) => { this._onSseError(err) },
      }, dimensions)
    },

    /* ── SSE 内部方法 ── */
    _startSse(mode) {
      this.sseGenerating = true
      this.sseReportMd = ''
      this.sseReportMode = mode
      this.sseSections = {}
      this.sseReportId = null
      this.sseProgress = { current: 0, total: 10, stages: [] }
      this.analyzeResult = null
      /* 新分析开始时清除旧的公司画像缓存 */
      if (mode === 'invest') {
        try { localStorage.removeItem(PROFILE_CACHE_KEY) } catch (_) {}
      }
    },

    _onSseProgress(data) {
      // 更新进度：stages 数组记录每个维度的状态
      const stages = [...this.sseProgress.stages]
      const idx = stages.findIndex(s => s.stage === data.stage)
      const entry = { stage: data.stage, label: data.label, status: data.status, error: data.error }
      if (idx >= 0) stages[idx] = entry
      else stages.push(entry)
      this.sseProgress = { current: data.current, total: data.total, stages }
    },

    async _onSseComplete(mode, data) {
      this.sseGenerating = false
      this.sseReportMd = data.report || ''
      this.sseSections = data.sections || {}
      this.sseReportId = data.report_id || null
      /* 报告生成后刷新自选股报告摘要 */
      this.fetchWatchlistReports().catch(() => {})
      if (mode === 'invest' && data.score !== undefined) {
        this.analyzeResult = {
          report: {
            stock_name: '', stock_code: '',
            score: data.score,
            decision: data.decision,
            summary: '',
          },
          report_id: data.report_id || null,
          message: '投研报告生成完成',
        }
        /* 投研报告完成后缓存公司画像到 localStorage，刷新不丢 */
        try {
          const cache = {
            stockCode: data.stock_code || '',
            stockName: data.stock_name || '',
            reportMd: data.report || '',
            reportId: data.report_id || null,
            score: data.score,
            decision: data.decision,
          }
          localStorage.setItem(PROFILE_CACHE_KEY, JSON.stringify(cache))
        } catch (_) {}
      }
      /* 飞书自动推送（仅投研报告模式，且用户开启了自动推送开关） */
      if (mode === 'invest' && data.report_id) {
        try {
          const autoPush = localStorage.getItem('stock_settings_feishu_push')
          if (autoPush === 'true') {
            await this.pushToFeishu(data.report_id)
          }
        } catch (_) {}
      }
      this.showToast(mode === 'data' ? '数据报告生成完成' : '投研报告生成完成')
    },

    _onSseError(err) {
      this.sseGenerating = false
      this.showToast('生成失败: ' + (err.message || '网络错误'))
    },

    /* 从 localStorage 恢复公司画像缓存（页面刷新/重新进入时调用） */
    restoreCachedProfile() {
      try {
        const raw = localStorage.getItem(PROFILE_CACHE_KEY)
        if (!raw) return false
        const cache = JSON.parse(raw)
        if (!cache.reportMd) return false
        this.sseReportMd = cache.reportMd
        this.sseReportMode = 'invest'
        this.sseReportId = cache.reportId || null
        if (cache.score !== undefined) {
          this.analyzeResult = {
            report: {
              stock_name: cache.stockName || '',
              stock_code: cache.stockCode || '',
              score: cache.score,
              decision: cache.decision || '',
              summary: '',
            },
            report_id: cache.reportId || null,
            message: '',
          }
        }
        return true
      } catch (_) {
        return false
      }
    },

    /* ── 报告 ── */
    async fetchDashboardReports() {
      this.loading = true
      try {
        const res = await api.getStockReports({ page: 1, page_size: 5 })
        if (res.code === 0) {
          this.dashboardReports = res.data.items
          this.dashboardReportsTotal = res.data.total
        }
      } catch (e) {
        this.showToast('获取报告列表失败')
      } finally {
        this.loading = false
      }
    },

    async fetchHistoryReports(page = 1, pageSize = 8, filters = {}) {
      this.loading = true
      try {
        const params = { page, page_size: pageSize }
        if (filters.search) params.search = filters.search
        if (filters.dateFrom) params.date_from = filters.dateFrom
        if (filters.dateTo) params.date_to = filters.dateTo
        if (filters.decision) params.decision = filters.decision
        const res = await api.getStockReports(params)
        if (res.code === 0) {
          this.historyReports = res.data.items
          this.historyReportsTotal = res.data.total
        }
      } catch (e) {
        this.showToast('获取报告列表失败')
      } finally {
        this.loading = false
      }
    },

    async fetchReportDetail(id) {
      this.currentReport = null
      this.reportLoading = true
      this.reportError = null
      try {
        const res = await api.getStockReportDetail(id)
        if (res.code === 0) this.currentReport = res.data
        else {
          this.reportError = res.message || '报告不存在'
          this.showToast(this.reportError)
        }
      } catch (e) {
        this.reportError = e.message || '获取报告详情失败'
        this.showToast(this.reportError)
      } finally {
        this.reportLoading = false
      }
    },

    /* 获取评分趋势数据（历史对比） */
    async fetchTrend(code) {
      try {
        const res = await api.getStockTrend(code)
        if (res.code === 0 && Array.isArray(res.data)) {
          this.trendPoints = res.data
        } else {
          this.trendPoints = []
        }
      } catch (e) {
        this.trendPoints = []
      }
    },

    /* ── 自选股 ── */
    async fetchWatchlist() {
      try {
        const res = await api.getStockWatchlist()
        if (res.code === 0) this.watchlist = res.data
      } catch (e) {
        this.showToast('获取自选股失败')
      }
    },

    /* 获取自选股各自最新报告摘要 */
    async fetchWatchlistReports() {
      try {
        const res = await api.getWatchlistReports()
        if (res.code === 0) this.watchlistReports = res.data
      } catch (_) { /* 静默失败 */ }
    },

    async addWatchlist(data) {
      const res = await api.addStockWatchlist(data)
      if (res.code === 0) {
        this.showToast(res.message)
        await this.fetchWatchlist()
      } else {
        this.showToast(res.message)
      }
      return res
    },

    async deleteWatchlist(stockCode) {
      try {
        const res = await api.deleteStockWatchlist(stockCode)
        if (res.code === 0) {
          this.showToast(res.message)
          await this.fetchWatchlist()
        } else {
          this.showToast(res.message || '删除失败')
        }
        return res
      } catch (e) {
        this.showToast('删除失败: ' + (e.message || '网络错误'))
      }
    },

    async updateWatchlist(stockCode, data) {
      try {
        const res = await api.updateStockWatchlist(stockCode, data)
        if (res.code === 0) {
          this.showToast(res.message)
          await this.fetchWatchlist()
        } else {
          this.showToast(res.message || '更新失败')
        }
        return res
      } catch (e) {
        this.showToast('更新失败: ' + (e.message || '网络错误'))
      }
    },

    /* ── 自选股分析 ── */
    async triggerWatchlistAnalyze() {
      this.analyzing = true
      try {
        const res = await api.triggerWatchlistAnalyze()
        if (res.code !== 0 || !res.task_id) {
          this.showToast(res.message || '触发失败')
          this.analyzing = false
          return
        }
        this.analyzeTaskId = res.task_id

        // 轮询结果：每 3s 一次，最多 120 次（360s，多只股票分析耗时更长）
        for (let i = 0; i < 120; i++) {
          await new Promise(r => setTimeout(r, 3000))
          try {
            const result = await api.getStockAnalyzeResult(this.analyzeTaskId)
            if (result.code !== 0) continue
            if (result.data.status === 'done') {
              this.showToast(result.data.message || '自选股分析完成')
              await this.fetchDashboardReports()
              this.analyzing = false
              return
            }
            if (result.data.status === 'error') {
              this.showToast('分析失败: ' + result.data.message)
              this.analyzing = false
              return
            }
          } catch (e) {
            /* 单次轮询失败不中断 */
          }
        }
        this.showToast('自选股分析超时，请稍后刷新查看')
      } catch (e) {
        this.showToast('触发失败: ' + (e.message || '网络错误'))
      } finally {
        this.analyzing = false
      }
    },

    /* ── 推送飞书 ── */
    async pushToFeishu(reportId) {
      try {
        const res = await api.pushStockReport(reportId)
        const msg = res.code === 0 ? (res.message || '推送成功') : (res.message || '推送失败')
        this.showToast(msg)
        return res
      } catch (e) {
        this.showToast('推送失败: ' + (e.message || '网络错误'))
      }
    },

    /* ── AI 问答 ── */
    async fetchChatSession(stockCode) {
      try {
        const res = await api.getChatSession(stockCode)
        if (res.code === 0) {
          this.chatSession = res.data.session
          this.chatMessages = res.data.messages || []
        }
      } catch (e) { this.showToast('加载问答会话失败') }
    },
    async fetchChatMessages(stockCode) {
      try {
        const res = await api.getChatMessages(stockCode)
        if (res.code === 0) this.chatMessages = res.data || []
      } catch (_) {}
    },

    /**
     * 发送问答（SSE 流式），内部管理 thinking/toolSteps/chatAsking 状态。
     * 组件只调此 action，不直接 import api（符合项目惯例）。
     *
     * 在途 SSE 隔离：请求发出后若用户已切换到其他股票（chatSession 变化），
     * 旧请求的回调按会话归属校验丢弃，不写入 chatMessages，避免跨会话污染；
     * 但最终收尾仍重置状态，防止 chatAsking 永久卡死。
     * @returns {AbortController}
     */
    askChat(stockCode, { question, report_id, stock_name }) {
      const reqCode = stockCode
      // 归属校验：会话未加载时视为当前（尚无可污染对象）；会话已知后必须与本次请求代码一致
      const isCurrent = () => !this.chatSession || this.chatSession.stock_code === reqCode

      this.chatAsking = true
      this.chatThinking = true
      this.chatToolSteps = []
      /* created_at 为前端发送时刻，供消息行元信息展示（历史消息用后端落库时间） */
      this.chatMessages.push({ role: 'user', content: question, tool_calls: null, created_at: new Date().toISOString() })

      let stepId = 0
      const controller = api.fetchChatAsk(stockCode, {
        question, report_id, stock_name,
      }, {
        onThinking: () => { if (isCurrent()) this.chatThinking = true },
        onToolDone: (d) => {
          // 归属不符：丢弃（不写入步骤卡片）
          if (!isCurrent()) return
          this.chatThinking = false
          stepId++
          this.chatToolSteps.push({
            id: stepId,
            label: d.label || d.name,
            status: d.ok ? 'done' : 'error',
          })
        },
        onDelta: (d) => {
          // 归属不符：丢弃增量，避免旧回答拼进新会话
          if (!isCurrent()) return
          const last = this.chatMessages[this.chatMessages.length - 1]
          if (last && last.role === 'assistant') last.content += d.text
          else this.chatMessages.push({ role: 'assistant', content: d.text, tool_calls: null, created_at: new Date().toISOString() })
        },
        onDone: (d) => {
          if (isCurrent()) {
            const last = this.chatMessages[this.chatMessages.length - 1]
            if (last && last.role === 'assistant') last.content = d.full
            else this.chatMessages.push({ role: 'assistant', content: d.full, tool_calls: null, created_at: new Date().toISOString() })
          }
          // 无论归属如何都重置状态，避免旧请求卡死新会话的输入
          this.chatThinking = false
          this.chatToolSteps = []
          this.chatAsking = false
        },
        onError: (e) => {
          if (isCurrent()) this.showToast(e.message || '回答失败')
          this.chatThinking = false
          this.chatToolSteps = []
          this.chatAsking = false
        },
        /* 流结束兜底：SSE 干净关闭但未 emit done/error 时，防止 chatAsking 永久卡住 */
        onStreamEnd: () => {
          this.chatThinking = false
          this.chatToolSteps = []
          this.chatAsking = false
        },
      })
      return controller
    },
  },
})
