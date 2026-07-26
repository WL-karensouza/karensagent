import { defineStore } from 'pinia'
import * as api from '../api/index.js'

export const useAgentStore = defineStore('agent', {
  state: () => ({
    /* Agent 注册表 */
    agents: [
      { id: 'ai_news', label: 'AI 前沿', badge: true },
      { id: 'stock', label: '股票分析', badge: false },
    ],

    /* AI 新闻仪表盘 */
    stats: {
      today_daily: 0,
      today_weekly: 0,
      week_reports: 0,
      today_pushes: 0,
      last_push: null,
    },
    loading: false,

    /* 推送历史 */
    pushHistory: [],

    /* Toast */
    toast: null,
  }),

  actions: {
    showToast(message, duration = 3000) {
      this.toast = message
      setTimeout(() => { this.toast = null }, duration)
    },

    /* ── AI 新闻仪表盘 ── */
    async fetchStats() {
      this.loading = true
      try {
        const res = await api.getDashboardStats()
        if (res.code === 0) this.stats = { ...this.stats, ...res.data }
      } catch (e) {
        this.showToast('获取仪表盘数据失败')
      } finally {
        this.loading = false
      }
    },

    /* ── 推送历史 ── */
    async fetchHistory(limit = 30) {
      try {
        const res = await api.getHistory(limit)
        if (res.code === 0) this.pushHistory = res.data
      } catch (e) {
        this.showToast('获取推送历史失败')
      }
    },

    /* ── 手动触发 ── */
    async triggerFull() {
      this.loading = true
      try {
        const res = await api.triggerFull()
        if (res.code === 0) {
          this.showToast('AI 新闻抓取+推送已启动，请稍后查看结果')
          // 延迟刷新统计数据
          setTimeout(() => this.fetchStats(), 5000)
        } else {
          this.showToast(res.message || '触发失败')
        }
      } catch (e) {
        this.showToast('触发失败: ' + (e.message || '网络错误'))
      } finally {
        this.loading = false
      }
    },
  },
})
