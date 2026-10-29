/* ═══════════════════════════════════════════
   会话加载竞态测试
   守护：fetchChatSession 不得被过期响应或归属不符的响应覆盖 store
   背景：切股票时若旧请求晚返回，会污染 chatSession，导致后续 askChat 的
        SSE 归属校验把回答全部丢弃（用户提问后收不到回答）
   ═══════════════════════════════════════════ */
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

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('fetchChatSession 竞态防护', () => {
  it('旧股票的响应晚返回时，不覆盖新股票的会话', async () => {
    const store = useStockStore()

    /* 手动控制两个请求的 resolve 时机，模拟「先发的后回」 */
    let resolveA
    let resolveB
    api.getChatSession.mockImplementation((code) => new Promise((resolve) => {
      if (code === 'A') resolveA = resolve
      else resolveB = resolve
    }))

    const pendingA = store.fetchChatSession('A')
    const pendingB = store.fetchChatSession('B')

    /* B 先返回 */
    resolveB({
      code: 0,
      data: { session: { stock_code: 'B' }, messages: [{ role: 'user', content: 'B 的消息' }] },
    })
    await pendingB
    expect(store.chatSession.stock_code).toBe('B')

    /* A 后返回：应被丢弃 */
    resolveA({
      code: 0,
      data: { session: { stock_code: 'A' }, messages: [{ role: 'user', content: 'A 的消息' }] },
    })
    await pendingA

    expect(store.chatSession.stock_code).toBe('B')
    expect(store.chatMessages[0].content).toBe('B 的消息')
  })

  it('响应归属与请求不符时，不写入 store', async () => {
    const store = useStockStore()
    api.getChatSession.mockResolvedValue({
      code: 0,
      data: { session: { stock_code: 'A' }, messages: [{ role: 'user', content: 'A 的消息' }] },
    })

    await store.fetchChatSession('B')

    expect(store.chatSession).toBe(null)
    expect(store.chatMessages).toEqual([])
  })
})
