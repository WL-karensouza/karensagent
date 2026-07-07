import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

/* Mock API 模块 —— 在系统边界 mock */
vi.mock('../api/index.js', () => ({
  getStockReports: vi.fn(),
  getStockReportDetail: vi.fn(),
  getStockWatchlist: vi.fn(),
  triggerStockAnalyze: vi.fn(),
  getStockAnalyzeResult: vi.fn(),
  triggerWatchlistAnalyze: vi.fn(),
  addStockWatchlist: vi.fn(),
  deleteStockWatchlist: vi.fn(),
  updateStockWatchlist: vi.fn(),
  pushStockReport: vi.fn(),
}))

import { useStockStore } from './stock.js'
import * as api from '../api/index.js'

/* 辅助：创建假报告 */
function fakeReport(i) {
  return {
    id: i,
    stock_code: '600' + String(i).padStart(3, '0'),
    stock_name: '测试股' + i,
    score: 75,
    decision: '看多',
    created_at: '2026-07-0' + ((i % 7) + 1) + 'T10:00:00',
    token_used: 1000,
  }
}

function fakeReports(count = 5) {
  return Array.from({ length: count }, (_, i) => fakeReport(i + 1))
}

describe('stock store — 报告列表拆分', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useStockStore()
    vi.clearAllMocks()
  })

  describe('fetchDashboardReports', () => {
    it('填充 dashboardReports 和 dashboardReportsTotal', async () => {
      const items = fakeReports(5)
      api.getStockReports.mockResolvedValue({
        code: 0,
        data: { items, total: 50 },
      })

      await store.fetchDashboardReports()

      expect(store.dashboardReports).toEqual(items)
      expect(store.dashboardReportsTotal).toBe(50)
    })

    it('不改变 historyReports', async () => {
      api.getStockReports.mockResolvedValue({
        code: 0,
        data: { items: fakeReports(5), total: 50 },
      })

      const beforeHistory = [...store.historyReports]
      await store.fetchDashboardReports()

      expect(store.historyReports).toEqual(beforeHistory)
    })
  })

  describe('fetchHistoryReports', () => {
    it('填充 historyReports 和 historyReportsTotal', async () => {
      const items = fakeReports(10)
      api.getStockReports.mockResolvedValue({
        code: 0,
        data: { items, total: 50 },
      })

      await store.fetchHistoryReports(2, 10)

      expect(store.historyReports).toEqual(items)
      expect(store.historyReportsTotal).toBe(50)
      expect(api.getStockReports).toHaveBeenCalledWith({ page: 2, page_size: 10 })
    })

    it('不改变 dashboardReports', async () => {
      api.getStockReports.mockResolvedValue({
        code: 0,
        data: { items: fakeReports(10), total: 50 },
      })

      const beforeDashboard = [...store.dashboardReports]
      await store.fetchHistoryReports(1, 10)

      expect(store.dashboardReports).toEqual(beforeDashboard)
    })
  })

  describe('两者独立不互相污染', () => {
    it('先 Dashboard 后 History 各自数据独立', async () => {
      const dashItems = fakeReports(5)
      const histItems = fakeReports(10).map(r => ({ ...r, id: r.id + 100 }))

      api.getStockReports
        .mockResolvedValueOnce({ code: 0, data: { items: dashItems, total: 5 } })
        .mockResolvedValueOnce({ code: 0, data: { items: histItems, total: 50 } })

      await store.fetchDashboardReports()
      await store.fetchHistoryReports(1, 10)

      expect(store.dashboardReports).toEqual(dashItems)
      expect(store.historyReports).toEqual(histItems)
      expect(store.dashboardReports).not.toEqual(store.historyReports)
    })
  })

  describe('fetchReportDetail', () => {
    it('请求前先清空 currentReport 防止旧数据闪烁', async () => {
      const reportA = fakeReport(1)
      const reportB = fakeReport(2)

      api.getStockReportDetail.mockResolvedValueOnce({ code: 0, data: reportA })
      await store.fetchReportDetail(1)
      expect(store.currentReport).toEqual(reportA)

      api.getStockReportDetail.mockResolvedValueOnce({ code: 0, data: reportB })
      const promiseB = store.fetchReportDetail(2)
      expect(store.currentReport).toBeNull()
      await promiseB
      expect(store.currentReport).toEqual(reportB)
    })

    it('请求成功后将数据写入 currentReport', async () => {
      const report = fakeReport(1)
      api.getStockReportDetail.mockResolvedValue({ code: 0, data: report })

      await store.fetchReportDetail(1)

      expect(store.currentReport).toEqual(report)
    })

    it('请求中 reportLoading 为 true，完成后为 false', async () => {
      api.getStockReportDetail.mockResolvedValue({ code: 0, data: fakeReport(1) })

      const promise = store.fetchReportDetail(1)
      expect(store.reportLoading).toBe(true)
      await promise
      expect(store.reportLoading).toBe(false)
    })

    it('请求失败时设置 reportError', async () => {
      api.getStockReportDetail.mockRejectedValue(new Error('网络错误'))

      await store.fetchReportDetail(1)

      expect(store.reportLoading).toBe(false)
      expect(store.reportError).toBeTruthy()
    })

    it('API 返回非零错误码时设置 reportError', async () => {
      api.getStockReportDetail.mockResolvedValue({ code: 1, message: '报告不存在' })

      await store.fetchReportDetail(1)

      expect(store.reportError).toBe('报告不存在')
      expect(store.currentReport).toBeNull()
    })

    it('再次请求成功可清除之前的 reportError', async () => {
      api.getStockReportDetail.mockRejectedValueOnce(new Error('网络错误'))
      await store.fetchReportDetail(1)
      expect(store.reportError).toBeTruthy()

      api.getStockReportDetail.mockResolvedValueOnce({ code: 0, data: fakeReport(2) })
      await store.fetchReportDetail(2)
      expect(store.reportError).toBeNull()
      expect(store.currentReport).not.toBeNull()
    })
  })

  describe('triggerWatchlistAnalyze', () => {
    it('触发后进入 analyzing 状态', async () => {
      api.triggerWatchlistAnalyze.mockResolvedValue({ code: 0, task_id: 'task-wl-1' })
      /* 直接返回 error 让轮询立即结束 */
      api.getStockAnalyzeResult.mockResolvedValue({
        code: 0,
        data: { status: 'error', message: 'stop' },
      })

      const promise = store.triggerWatchlistAnalyze()
      expect(store.analyzing).toBe(true)
      await promise
      expect(store.analyzing).toBe(false)
    })

    it('分析完成后自动刷新 Dashboard 报告列表', async () => {
      api.triggerWatchlistAnalyze.mockResolvedValue({ code: 0, task_id: 'task-wl-2' })
      api.getStockAnalyzeResult.mockResolvedValue({
        code: 0,
        data: { status: 'done', message: '分析完成' },
      })
      /* 跟踪 fetchDashboardReports 是否被调用 */
      const spy = vi.spyOn(store, 'fetchDashboardReports').mockResolvedValue()

      await store.triggerWatchlistAnalyze()

      expect(spy).toHaveBeenCalledTimes(1)
      spy.mockRestore()
    })

    it('触发失败时不在 analyzing 状态', async () => {
      api.triggerWatchlistAnalyze.mockResolvedValue({ code: 1, message: '服务异常' })

      await store.triggerWatchlistAnalyze()

      expect(store.analyzing).toBe(false)
    })

    it('分析超时后给出提示并停止 analyzing', async () => {
      vi.useFakeTimers()
      api.triggerWatchlistAnalyze.mockResolvedValue({ code: 0, task_id: 'task-wl-3' })
      /* 始终返回 pending，触发超时 */
      api.getStockAnalyzeResult.mockResolvedValue({
        code: 0,
        data: { status: 'pending' },
      })

      const promise = store.triggerWatchlistAnalyze()
      /* 快进 20 轮 × 3s = 60s */
      for (let i = 0; i < 20; i++) {
        await vi.advanceTimersByTimeAsync(3000)
      }
      await promise

      expect(store.analyzing).toBe(false)
      vi.useRealTimers()
    })
  })
})
