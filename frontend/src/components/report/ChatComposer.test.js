/* ═══════════════════════════════════════════
   ChatComposer 测试
   守护：键盘提交契约（Enter/Shift+Enter/中文输入法/空输入）、
        装饰按钮不可达性、密度分档
   ═══════════════════════════════════════════ */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ChatComposer from './ChatComposer.vue'

function mountComposer(props = {}) {
  return mount(ChatComposer, { props: { modelValue: '', ...props } })
}

/* Vue Test Utils 的 trigger 无法直接设置 KeyboardEvent 的只读属性 isComposing，
   这里手动构造事件，确保「中文输入法选词回车」场景被真实模拟 */
async function triggerEnter(wrapper, init = {}) {
  const event = new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true, ...init })
  Object.defineProperty(event, 'isComposing', { value: init.isComposing || false })
  wrapper.find('.composer-textarea').element.dispatchEvent(event)
  await wrapper.vm.$nextTick()
}

describe('ChatComposer 输入交互', () => {
  it('Enter 触发 send 事件', async () => {
    const w = mountComposer({ modelValue: '风险点？' })
    await triggerEnter(w)
    expect(w.emitted('send')).toHaveLength(1)
  })

  it('Shift+Enter 不触发 send', async () => {
    const w = mountComposer({ modelValue: '第一行' })
    await triggerEnter(w, { shiftKey: true })
    expect(w.emitted('send')).toBeUndefined()
  })

  it('中文输入法选词时 Enter 不触发 send', async () => {
    const w = mountComposer({ modelValue: '平安' })
    await triggerEnter(w, { isComposing: true })
    expect(w.emitted('send')).toBeUndefined()
  })

  it('空输入时 Enter 不触发 send', async () => {
    const w = mountComposer({ modelValue: '   ' })
    await triggerEnter(w)
    expect(w.emitted('send')).toBeUndefined()
  })

  it('点击发送键触发 send', async () => {
    const w = mountComposer({ modelValue: '评分依据' })
    await w.find('.composer-send').trigger('click')
    expect(w.emitted('send')).toHaveLength(1)
  })

  it('disabled 时发送键禁用且不触发 send', async () => {
    const w = mountComposer({ modelValue: '评分依据', disabled: true })
    expect(w.find('.composer-send').attributes('disabled')).toBeDefined()
    await w.find('.composer-send').trigger('click')
    expect(w.emitted('send')).toBeUndefined()
  })

  it('不再渲染任何装饰按钮，工具行只有发送键', () => {
    const w = mountComposer()
    /* @ 图标与 Auto/Settings/麦克风等占位件已全部移除 */
    expect(w.find('.composer-at').exists()).toBe(false)
    expect(w.find('.composer-tool').exists()).toBe(false)
    expect(w.find('.composer-mic').exists()).toBe(false)
    const buttons = w.findAll('.composer-tools button')
    expect(buttons).toHaveLength(1)
    expect(buttons[0].classes()).toContain('composer-send')
  })

  it('density 影响根元素类名', () => {
    expect(mountComposer({ density: 'compact' }).find('.composer-tray').classes()).toContain('is-compact')
    expect(mountComposer({ density: 'landing' }).find('.composer-tray').classes()).toContain('is-landing')
  })
})
