import { defineStore } from 'pinia'
import * as api from '../api/index.js'

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

    /* 分析状态 */
    analyzing: false,
    analyzeTaskId: null,
    analyzeResult: null,

    /* 加载 */
    loading: false,
    reportLoading: false,
    reportError: null,

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

        // 轮询结果：每 3s 一次，最多 20 次（60s）
        for (let i = 0; i < 20; i++) {
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

    async fetchHistoryReports(page = 1, pageSize = 10) {
      this.loading = true
      try {
        const res = await api.getStockReports({ page, page_size: pageSize })
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

    /* ── 自选股 ── */
    async fetchWatchlist() {
      try {
        const res = await api.getStockWatchlist()
        if (res.code === 0) this.watchlist = res.data
      } catch (e) {
        this.showToast('获取自选股失败')
      }
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
      const res = await api.deleteStockWatchlist(stockCode)
      if (res.code === 0) {
        this.showToast(res.message)
        await this.fetchWatchlist()
      }
      return res
    },

    async updateWatchlist(stockCode, data) {
      const res = await api.updateStockWatchlist(stockCode, data)
      if (res.code === 0) {
        this.showToast(res.message)
        await this.fetchWatchlist()
      }
      return res
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

        // 轮询结果：每 3s 一次，最多 20 次（60s）
        for (let i = 0; i < 20; i++) {
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
  },
})
