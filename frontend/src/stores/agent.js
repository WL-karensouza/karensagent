import { defineStore } from 'pinia'
import * as api from '../api/index.js'

export const useAgentStore = defineStore('agent', {
  state: () => ({
    /* Agent 注册表 */
    agents: [
      { id: 'github', label: 'GitHub 热榜', badge: true },
      { id: 'stock', label: '股票分析', badge: false },
    ],

    /* 仪表盘 */
    stats: {
      today_repos: 0,
      week_unique_repos: 0,
      week_news: 0,
      last_push: null,
      push_time: '09:00',
      today_pushes: 0,
      today_news: 0,
    },
    loading: false,

    /* 预览 */
    trends: [],
    news: [],
    availableDates: [],

    /* 历史 */
    pushHistory: [],

    /* 配置 */
    keywords: [],
    webhooks: { configured: false },

    /* Toast */
    toast: null,
  }),

  actions: {
    showToast(message, duration = 3000) {
      this.toast = message
      setTimeout(() => { this.toast = null }, duration)
    },

    /* ── 仪表盘 ── */
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

    /* 保留旧名兼容 */
    async fetchDashboard() {
      return this.fetchStats()
    },

    /* ── 预览 ── */
    async fetchTrends(params = {}) {
      try {
        const res = await api.getTrends({ limit: 50, ...params })
        if (res.code === 0) this.trends = res.data
      } catch (e) {
        this.showToast('获取趋势数据失败')
      }
    },

    async fetchNews(params = {}) {
      try {
        const res = await api.getNews({ limit: 5, ...params })
        if (res.code === 0) this.news = res.data
      } catch (e) {
        this.showToast('获取资讯失败')
      }
    },

    async fetchAvailableDates() {
      try {
        const res = await api.getAvailableDates()
        if (res.code === 0) this.availableDates = res.data
      } catch (e) {
        /* 静默失败 */
      }
    },

    /* ── 历史 ── */
    async fetchHistory(limit = 30) {
      try {
        const res = await api.getHistory(limit)
        if (res.code === 0) this.pushHistory = res.data
      } catch (e) {
        this.showToast('获取推送历史失败')
      }
    },

    /* ── 触发 ── */
    async triggerAction(action) {
      this.loading = true
      try {
        const fn = {
          fetch: api.triggerFetch,
          push: api.triggerPush,
          full: api.triggerFull,
        }[action]
        if (!fn) {
          this.showToast('未知操作')
          return
        }

        const res = await fn()
        if (res.code !== 0 || !res.task_id) {
          this.showToast(res.message || '触发失败')
          return
        }

        const taskId = res.task_id
        // 轮询结果：每 3s 一次，最多 20 次（60s）
        for (let i = 0; i < 20; i++) {
          await new Promise(r => setTimeout(r, 3000))
          try {
            const result = await api.getTaskResult(taskId)
            if (result.code !== 0) continue
            if (result.data.status === 'done') {
              this.showToast(result.data.message || '操作完成')
              await this.fetchStats()
              this.loading = false
              return
            }
          } catch (e) {
            // 单次轮询失败不中断，继续重试
          }
        }

        // 超时
        this.showToast('操作超时，请稍后刷新查看结果')
        await this.fetchStats()
      } catch (e) {
        this.showToast('操作失败: ' + (e.message || '网络错误'))
      } finally {
        this.loading = false
      }
    },

    /* ── 关键词 ── */
    async fetchKeywords() {
      try {
        const res = await api.getKeywords()
        if (res.code === 0) this.keywords = res.data
      } catch (e) {
        this.showToast('获取关键词失败')
      }
    },

    async addKeyword(data) {
      const res = await api.addKeyword(data)
      if (res.code === 0) {
        this.showToast(res.message)
        await this.fetchKeywords()
      } else {
        this.showToast(res.message)
      }
      return res
    },

    async updateKeyword(keyword, data) {
      const res = await api.updateKeyword(keyword, data)
      if (res.code === 0) {
        this.showToast(res.message)
        await this.fetchKeywords()
      }
      return res
    },

    async deleteKeyword(keyword) {
      const res = await api.deleteKeyword(keyword)
      if (res.code === 0) {
        this.showToast(res.message)
        await this.fetchKeywords()
      }
      return res
    },

    /* ── 飞书 Webhook ── */
    async fetchWebhook() {
      try {
        const res = await api.getWebhook()
        if (res.code === 0) this.webhooks = res.data
      } catch (e) {
        this.showToast('获取 Webhook 配置失败')
      }
    },

    async updateWebhook(url) {
      const res = await api.updateWebhook(url)
      if (res.code === 0) {
        this.showToast(res.message)
        await this.fetchWebhook()
      }
      return res
    },
  },
})
