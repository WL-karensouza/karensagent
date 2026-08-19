import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('../api/index.js', () => ({
  fetchChatAsk: vi.fn(),
  getChatSession: vi.fn(),
  getChatMessages: vi.fn(),
  getStockReports: vi.fn(),
}))

import { useStockStore } from './stock.js'
import * as api from '../api/index.js'

/* 捕获 fetchChatAsk 的回调，模拟后端 SSE 事件 */
function captureCallbacks() {
  let cb = null
  api.fetchChatAsk.mockImplementation((code, body, callbacks) => {
    cb = callbacks
    return { abort: vi.fn() }
  })
  return () => cb
}

describe('askChat 思考过程面板状态', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useStockStore()
    vi.clearAllMocks()
    store.chatSession = { stock_code: '000858' }
  })

  it('phase understand 推入理解行', () => {
    const getCb = captureCallbacks()
    store.askChat('000858', { question: 'q', report_id: null, stock_name: '五粮液' })
    getCb().onPhase({ phase: 'understand' })

    expect(store.chatSteps).toHaveLength(1)
    expect(store.chatSteps[0]).toMatchObject({ type: 'understand', label: '理解问题', status: 'running' })
  })

  it('tool_start 追加工具行，tool_done 更新为 done', () => {
    const getCb = captureCallbacks()
    store.askChat('000858', { question: 'q', report_id: null, stock_name: '五粮液' })
    const cb = getCb()

    cb.onToolStart({ name: 'search_news', label: '查询近期新闻' })
    expect(store.chatSteps).toHaveLength(1)
    expect(store.chatSteps[0]).toMatchObject({ type: 'tool', label: '查询近期新闻', status: 'running' })

    cb.onToolDone({ name: 'search_news', label: '查询近期新闻', ok: true })
    expect(store.chatSteps[0].status).toBe('done')
  })

  it('tool_done ok=false 更新为 error', () => {
    const getCb = captureCallbacks()
    store.askChat('000858', { question: 'q', report_id: null, stock_name: '五粮液' })
    const cb = getCb()

    cb.onToolStart({ name: 'search_news', label: '查询近期新闻' })
    cb.onToolDone({ name: 'search_news', label: '查询近期新闻', ok: false })
    expect(store.chatSteps[0].status).toBe('error')
  })

  it('understand_done 把理解行从 running 置为 done（方案 B 打勾）', () => {
    const getCb = captureCallbacks()
    store.askChat('000858', { question: 'q', report_id: null, stock_name: '五粮液' })
    const cb = getCb()

    cb.onPhase({ phase: 'understand' })
    expect(store.chatSteps[0].status).toBe('running')
    cb.onUnderstandDone({})
    expect(store.chatSteps[0].status).toBe('done')
  })

  it('understand_done 幂等：已是 done 不再改动', () => {
    const getCb = captureCallbacks()
    store.askChat('000858', { question: 'q', report_id: null, stock_name: '五粮液' })
    const cb = getCb()

    cb.onPhase({ phase: 'understand' })
    cb.onUnderstandDone({})
    cb.onUnderstandDone({})
    expect(store.chatSteps.filter(s => s.status === 'done').length).toBe(1)
  })

  it('phase answer 推入生成行', () => {
    const getCb = captureCallbacks()
    store.askChat('000858', { question: 'q', report_id: null, stock_name: '五粮液' })
    getCb().onPhase({ phase: 'answer' })

    expect(store.chatSteps[store.chatSteps.length - 1])
      .toMatchObject({ type: 'answer', label: '生成回答', status: 'running' })
  })

  it('首个 delta 清空 chatSteps（卡片闭合）并追加回答', () => {
    const getCb = captureCallbacks()
    store.askChat('000858', { question: 'q', report_id: null, stock_name: '五粮液' })
    const cb = getCb()

    cb.onPhase({ phase: 'understand' })
    cb.onDelta({ text: '你好' })

    expect(store.chatSteps).toEqual([])
    expect(store.chatMessages[store.chatMessages.length - 1])
      .toMatchObject({ role: 'assistant', content: '你好' })
  })

  it('onError 清空 chatSteps', () => {
    const getCb = captureCallbacks()
    store.askChat('000858', { question: 'q', report_id: null, stock_name: '五粮液' })
    const cb = getCb()

    cb.onPhase({ phase: 'understand' })
    cb.onError(new Error('失败'))
    expect(store.chatSteps).toEqual([])
    expect(store.chatAsking).toBe(false)
  })

  it('onStreamEnd 清空 chatSteps（防卡死兜底）', () => {
    const getCb = captureCallbacks()
    store.askChat('000858', { question: 'q', report_id: null, stock_name: '五粮液' })
    getCb().onStreamEnd()

    expect(store.chatSteps).toEqual([])
    expect(store.chatAsking).toBe(false)
  })

  it('新一轮提问重置 chatSteps', () => {
    const getCb = captureCallbacks()
    store.askChat('000858', { question: 'q', report_id: null, stock_name: '五粮液' })
    getCb().onPhase({ phase: 'understand' })
    expect(store.chatSteps).toHaveLength(1)

    // 新一轮提问
    api.fetchChatAsk.mockClear()
    store.askChat('000858', { question: 'q2', report_id: null, stock_name: '五粮液' })
    expect(store.chatSteps).toEqual([])
  })

  it('连续相同 label 的工具行合并为一行', () => {
    const getCb = captureCallbacks()
    store.askChat('000858', { question: 'q', report_id: null, stock_name: '五粮液' })
    const cb = getCb()

    cb.onToolStart({ name: 'get_stock_financials', label: '核对财务数据' })
    cb.onToolStart({ name: 'get_stock_financials', label: '核对财务数据' })
    cb.onToolStart({ name: 'get_stock_financials', label: '核对财务数据' })
    expect(store.chatSteps.filter(s => s.type === 'tool')).toHaveLength(1)

    cb.onToolDone({ name: 'get_stock_financials', label: '核对财务数据', ok: true })
    expect(store.chatSteps.find(s => s.type === 'tool').status).toBe('done')
  })

  it('不同 label 的工具行不合并', () => {
    const getCb = captureCallbacks()
    store.askChat('000858', { question: 'q', report_id: null, stock_name: '五粮液' })
    const cb = getCb()

    cb.onToolStart({ name: 'search_news', label: '查询近期新闻' })
    cb.onToolStart({ name: 'get_stock_financials', label: '核对财务数据' })
    expect(store.chatSteps.filter(s => s.type === 'tool')).toHaveLength(2)
  })
})
