import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

/* ── 用 vi.hoisted 解决 mock 提升问题 ── */
const { mockStore, mockPush } = vi.hoisted(() => {
  const state = {
    analyzing: false,
    analyzeResult: null,
    dashboardReports: [],
    dashboardReportsTotal: 0,
    watchlist: [],
    fetchWatchlist: vi.fn().mockResolvedValue(),
    fetchDashboardReports: vi.fn().mockResolvedValue(),
    triggerAnalyze: vi.fn().mockResolvedValue(),
  }
  return {
    mockStore: state,
    mockPush: vi.fn(),
  }
})

/* ── Mock router ── */
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockPush }),
  useRoute: () => ({ path: '/agent/stock' }),
}))

/* ── Mock stock store ── */
vi.mock('../../stores/stock.js', () => ({
  useStockStore: () => mockStore,
}))

/* ── Mock utils ── */
vi.mock('../../utils/stock.js', () => ({
  scoreColor: () => '#166534',
  decisionBadge: (d) => (d ? '🟢 ' + d : ''),
  DIMENSIONS: [
    { key: 'market', label: '市场行情', fetcher: 'market_data' },
    { key: 'finance', label: '财务分析', fetcher: 'financials' },
    { key: 'news', label: '新闻事件', fetcher: 'news_events' },
    { key: 'risk', label: '风险评估', fetcher: 'risk' },
    { key: 'env', label: '市场环境', fetcher: 'market_env' },
  ],
  ANALYSIS_STATE: {
    IDLE: 'idle',
    RUNNING: 'running',
    DONE: 'done',
    PARTIAL: 'partial',
    ERROR: 'error',
  },
}))

import StockDashboard from './StockDashboard.vue'

/* 辅助：重置 mock store */
function resetStore(overrides = {}) {
  Object.assign(mockStore, {
    analyzing: false,
    analyzeResult: null,
    dashboardReports: [],
    dashboardReportsTotal: 0,
    watchlist: [],
    showToast: vi.fn(),
    fetchWatchlist: vi.fn().mockResolvedValue(),
    fetchDashboardReports: vi.fn().mockResolvedValue(),
    triggerAnalyze: vi.fn().mockResolvedValue(),
  }, overrides)
}

function mountDashboard(overrides = {}) {
  resetStore(overrides)
  return mount(StockDashboard, {
    global: {
      stubs: { RouterLink: { template: '<a><slot/></a>' } },
    },
  })
}

describe('StockDashboard — 仪表盘页面', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    resetStore()
  })

  /* ═══════════════════════════════════════════
   * 1. 搜索框 + 分析触发
   * ═══════════════════════════════════════════ */
  describe('搜索框', () => {
    it('输入股票代码后按回车触发分析', async () => {
      const wrapper = mountDashboard()

      await wrapper.find('input[placeholder*="600519"]').setValue('600519')
      await wrapper.find('input[placeholder*="600519"]').trigger('keyup.enter')

      expect(mockStore.triggerAnalyze).toHaveBeenCalledWith('600519')
    })

    it('点击"开始分析"按钮触发分析', async () => {
      const wrapper = mountDashboard()

      await wrapper.find('input[placeholder*="600519"]').setValue('000858')
      await wrapper.find('.btn-primary').trigger('click')

      expect(mockStore.triggerAnalyze).toHaveBeenCalledWith('000858')
    })

    it('空输入时不触发分析', async () => {
      const wrapper = mountDashboard()

      await wrapper.find('.btn-primary').trigger('click')

      expect(mockStore.triggerAnalyze).not.toHaveBeenCalled()
    })

    it('分析中输入框禁用', () => {
      const wrapper = mountDashboard({ analyzing: true })

      const input = wrapper.find('input[placeholder*="600519"]')
      expect(input.element.disabled).toBe(true)
    })
  })

  /* ═══════════════════════════════════════════
   * 2. 维度目录
   * ═══════════════════════════════════════════ */
  describe('维度目录 (TOC)', () => {
    it('渲染 5 个维度项', () => {
      const wrapper = mountDashboard()
      const items = wrapper.findAll('.toc-item')
      expect(items).toHaveLength(5)
    })

    it('第一个维度默认激活', () => {
      const wrapper = mountDashboard()
      const first = wrapper.find('.toc-item.active')
      expect(first.exists()).toBe(true)
    })

    it('点击维度项切换 active 状态', async () => {
      const wrapper = mountDashboard()
      const items = wrapper.findAll('.toc-item')

      await items[1].trigger('click')

      const activeItems = wrapper.findAll('.toc-item.active')
      expect(activeItems).toHaveLength(1)
    })

    it('点击维度项切换对应面板可见性', async () => {
      const wrapper = mountDashboard()

      /* 默认第一个面板可见：v-show 控制 display */
      const panelMarket = wrapper.find('#panel-market')
      const panelFinance = wrapper.find('#panel-finance')
      expect(panelMarket.element.style.display).not.toBe('none')

      /* 点击第二个维度 → 第二个面板可见 */
      await wrapper.findAll('.toc-item')[1].trigger('click')
      await wrapper.vm.$nextTick()
      expect(panelFinance.element.style.display).not.toBe('none')
    })
  })

  /* ═══════════════════════════════════════════
   * 3. 分析中状态
   * ═══════════════════════════════════════════ */
  describe('分析中状态', () => {
    it('analyzing=true 时显示进度区域', () => {
      const wrapper = mountDashboard({ analyzing: true })
      const progress = wrapper.find('.progress-line')
      expect(progress.exists()).toBe(true)
      expect(progress.text()).not.toBe('')
    })

    it('analyzing=false 时进度区域为空', () => {
      const wrapper = mountDashboard({ analyzing: false })
      const progress = wrapper.find('.progress-line')
      expect(progress.text()).toBe('')
    })
  })

  /* ═══════════════════════════════════════════
   * 4. 完成状态
   * ═══════════════════════════════════════════ */
  describe('完成状态', () => {
    it('analyzeResult 存在时显示"生成综合报告"按钮', () => {
      const wrapper = mountDashboard({
        analyzeResult: {
          report_id: 1,
          report: { stock_name: '测试', score: 75, decision: '看多' },
        },
      })

      expect(wrapper.find('.btn-report').exists()).toBe(true)
    })

    it('无 analyzeResult 时不显示报告按钮', () => {
      const wrapper = mountDashboard({ analyzeResult: null })
      expect(wrapper.find('.btn-report').exists()).toBe(false)
    })
  })

  /* ═══════════════════════════════════════════
   * 5. 缺失维度状态
   * ═══════════════════════════════════════════ */
  describe('缺失维度', () => {
    it('风险评估面板包含缺失状态提示', () => {
      const wrapper = mountDashboard()
      const riskPanel = wrapper.find('#panel-risk')
      expect(riskPanel.exists()).toBe(true)
    })
  })

  /* ═══════════════════════════════════════════
   * 6. 最近报告区域
   * ═══════════════════════════════════════════ */
  describe('最近报告区域', () => {
    it('有报告时渲染报告列表', () => {
      const wrapper = mountDashboard({
        dashboardReports: [
          {
            id: 1, stock_code: '600519', stock_name: '贵州茅台',
            score: 82, decision: '看多', created_at: '2026-07-10T10:00',
          },
        ],
        dashboardReportsTotal: 1,
      })

      expect(wrapper.find('.reports-section').exists()).toBe(true)
    })
  })

  /* ═══════════════════════════════════════════
   * 7. 底部自选股轮播
   * ═══════════════════════════════════════════ */
  describe('自选股轮播', () => {
    it('自选股 ≤ 3 支时仍显示导航控件，箭头禁用', () => {
      const wrapper = mountDashboard({
        watchlist: [{ stock_code: '600519', stock_name: '贵州茅台' }],
      })

      /* 导航始终显示，不再隐藏 */
      expect(wrapper.find('.watchlist-nav').classes('hidden')).toBe(false)
      /* 仅 1 支股票 → maxSlide=0，左右箭头都禁用 */
      const arrows = wrapper.findAll('.watchlist-arrow')
      expect(arrows[0].element.disabled).toBe(true)
      expect(arrows[1].element.disabled).toBe(true)
    })

    it('自选股 > 3 支时箭头可用，dots 显示', () => {
      const wrapper = mountDashboard({
        watchlist: [
          { stock_code: '600519', stock_name: '贵州茅台' },
          { stock_code: '000858', stock_name: '五粮液' },
          { stock_code: '300750', stock_name: '宁德时代' },
          { stock_code: '601318', stock_name: '中国平安' },
        ],
      })

      expect(wrapper.find('.watchlist-nav').exists()).toBe(true)
      /* 4 支 → 1 dot */
      expect(wrapper.findAll('.watchlist-dot')).toHaveLength(1)
    })
  })
})
