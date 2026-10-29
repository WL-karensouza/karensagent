/* ═══════════════════════════════════════════
   AiChatPanel 双态测试
   守护：收拢/展开判定、会话归属守卫、接口失败降级
   （纯 CSS 视觉部分由浏览器目检验证）
   ═══════════════════════════════════════════ */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('../../stores/stock.js', () => ({ useStockStore: () => globalThis.__store }))
vi.mock('../../api/index.js', () => ({}))

import AiChatPanel from './AiChatPanel.vue'

function makeStore(overrides = {}) {
  return {
    currentReport: { id: 1, stock_code: '000001', stock_name: '平安银行' },
    chatMessages: [], chatSession: null, chatSteps: [], chatAsking: false,
    fetchChatSession: vi.fn().mockResolvedValue(undefined),
    askChat: vi.fn(),
    ...overrides,
  }
}

beforeEach(() => { setActivePinia(createPinia()) })

describe('AiChatPanel 双态', () => {
  it('无历史消息时处于收拢态', async () => {
    globalThis.__store = makeStore()
    const w = mount(AiChatPanel)
    await flushPromises()
    expect(w.find('.ai-panel').classes()).toContain('is-collapsed')
  })

  it('有历史消息时处于展开态', async () => {
    globalThis.__store = makeStore({
      chatMessages: [{ role: 'user', content: '评分依据？', created_at: '' }],
      chatSession: { stock_code: '000001' },
    })
    const w = mount(AiChatPanel)
    await flushPromises()
    expect(w.find('.ai-panel').classes()).toContain('is-expanded')
  })

  it('会话归属不匹配时不展开也不渲染消息', async () => {
    globalThis.__store = makeStore({
      chatMessages: [{ role: 'user', content: '上一只股票的问题', created_at: '' }],
      chatSession: { stock_code: '600519' },   // 归属与当前 000001 不符
    })
    const w = mount(AiChatPanel)
    await flushPromises()
    expect(w.find('.ai-panel').classes()).toContain('is-collapsed')
    expect(w.text()).not.toContain('上一只股票的问题')
  })

  it('会话接口失败时按无历史收拢，不阻断页面', async () => {
    globalThis.__store = makeStore({
      fetchChatSession: vi.fn().mockRejectedValue(new Error('network down')),
    })
    const w = mount(AiChatPanel)
    await flushPromises()
    expect(w.find('.ai-panel').classes()).toContain('is-collapsed')
  })

  it('收拢态下输入并发送会调用 askChat', async () => {
    const store = makeStore()
    globalThis.__store = store
    const w = mount(AiChatPanel)
    await flushPromises()
    await w.find('.ai-input input').setValue('这只票的风险点？')
    await w.find('.ai-input button').trigger('click')
    expect(store.askChat).toHaveBeenCalledWith('000001', expect.objectContaining({
      question: '这只票的风险点？',
    }))
  })

  it('发送中禁用发送按钮', async () => {
    globalThis.__store = makeStore({ chatAsking: true })
    const w = mount(AiChatPanel)
    await flushPromises()
    expect(w.find('.ai-input button').attributes('disabled')).toBeDefined()
  })
})
