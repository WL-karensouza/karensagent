import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import * as api from './index.js'

/* 构造带 SSE 数据的 ReadableStream */
function sseStream(bodyStr) {
  const encoder = new TextEncoder()
  return new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(bodyStr))
      controller.close()
    },
  })
}

describe('fetchChatAsk SSE 解析', () => {
  let originalFetch

  beforeEach(() => { originalFetch = globalThis.fetch })
  afterEach(() => { globalThis.fetch = originalFetch })

  it('解析 phase/tool_start/tool_done/delta/done 全链路', async () => {
    const body = [
      'data: {"type":"phase","phase":"understand"}\n\n',
      'data: {"type":"tool_start","name":"search_news","label":"查询近期新闻"}\n\n',
      'data: {"type":"tool_done","name":"search_news","label":"查询近期新闻","ok":true}\n\n',
      'data: {"type":"delta","text":"你好"}\n\n',
      'data: {"type":"done","full":"你好"}\n\n',
    ].join('')
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, body: sseStream(body) })

    const calls = []
    await new Promise((resolve) => {
      api.fetchChatAsk('000858', { question: 'q' }, {
        onPhase: (d) => calls.push(`phase:${d.phase}`),
        onToolStart: (d) => calls.push(`tool_start:${d.label}`),
        onToolDone: (d) => calls.push(`tool_done:${d.label}:${d.ok}`),
        onDelta: (d) => calls.push(`delta:${d.text}`),
        onDone: (d) => calls.push(`done:${d.full}`),
        onStreamEnd: resolve,
      })
    })

    expect(calls).toEqual([
      'phase:understand',
      'tool_start:查询近期新闻',
      'tool_done:查询近期新闻:true',
      'delta:你好',
      'done:你好',
    ])
  })

  it('废弃的 thinking 事件不触发回调', async () => {
    const body = 'data: {"type":"thinking"}\n\n' +
                 'data: {"type":"done","full":"答"}\n\n'
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, body: sseStream(body) })

    const calls = []
    await new Promise((resolve) => {
      api.fetchChatAsk('000858', { question: 'q' }, {
        onThinking: () => calls.push('thinking'),
        onDone: (d) => calls.push(`done:${d.full}`),
        onStreamEnd: resolve,
      })
    })

    expect(calls).toEqual(['done:答'])
  })

  it('error 事件触发 onError', async () => {
    const body = 'data: {"type":"error","message":"失败啦"}\n\n'
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, body: sseStream(body) })

    const calls = []
    await new Promise((resolve) => {
      api.fetchChatAsk('000858', { question: 'q' }, {
        onError: (e) => calls.push(e.message),
        onStreamEnd: resolve,
      })
    })

    expect(calls).toEqual(['失败啦'])
  })
})
