/* ═══════════════════════════════════════════
   CharacterBubble 测试
   直接 mount 无 TresCanvas 上下文，mock useTres/useLoop
   验证渲染容器存在 + show() 后文本气泡出现
   ═══════════════════════════════════════════ */
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import CharacterBubble from './CharacterBubble.vue'

// mock @tresjs/core：测试用 mount 直接挂载，没有 TresCanvas 提供
// useTres/useLoop 的注入上下文，必须替换成最小假实现避免报错
vi.mock('@tresjs/core', () => ({
  useTres: () => ({ camera: { value: null } }),
  useLoop: () => ({ onRender: vi.fn() }),
}))

describe('CharacterBubble', () => {
  it('渲染容器', () => {
    const wrapper = mount(CharacterBubble, { props: { target: { x: 0, y: 0, z: 0 } } })
    expect(wrapper.exists()).toBe(true)
  })

  it('调用 show 后出现文本气泡', async () => {
    const wrapper = mount(CharacterBubble, { props: { target: { x: 0, y: 0, z: 0 } } })
    await wrapper.vm.show('你好')
    const text = wrapper.text()
    expect(text).toContain('你好')
    wrapper.unmount() // 清理 show 内的 setTimeout，避免计时器泄漏
  })
})
