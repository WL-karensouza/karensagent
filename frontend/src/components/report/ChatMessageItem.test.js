/* ═══════════════════════════════════════════
   ChatMessageItem 测试
   守护气泡的结构契约：role → 类名映射、markdown 渲染
   （纯 CSS 视觉部分无法在 happy-dom 中断言，由浏览器目检验证）
   ═══════════════════════════════════════════ */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ChatMessageItem from './ChatMessageItem.vue'

describe('ChatMessageItem 气泡结构', () => {
  it('用户消息渲染 user 类名且内容为 markdown 转 HTML', () => {
    const wrapper = mount(ChatMessageItem, {
      props: { message: { role: 'user', content: '**加粗**', created_at: '2026-10-29T10:00:00Z' } },
    })
    expect(wrapper.find('.chat-msg').classes()).toContain('user')
    expect(wrapper.find('.chat-bubble').html()).toContain('<strong>加粗</strong>')
  })

  it('助理消息渲染 assistant 类名', () => {
    const wrapper = mount(ChatMessageItem, {
      props: { message: { role: 'assistant', content: '你好', created_at: '2026-10-29T10:00:00Z' } },
    })
    expect(wrapper.find('.chat-msg').classes()).toContain('assistant')
  })
})
