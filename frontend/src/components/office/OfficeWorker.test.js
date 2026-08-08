/* ═══════════════════════════════════════════
   OfficeWorker 测试
   验证 props 接口不变 + 自建角色可挂载 + 点击触发 select
   改造后组件不再使用 @tresjs/cientos 的 useFBX，故不 mock cientos
   mock @tresjs/core（happy-dom 无 WebGL 环境）
   ═══════════════════════════════════════════ */
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import OfficeWorker from './OfficeWorker.vue'

// stub 掉 @tresjs/core（happy-dom 无 WebGL 渲染）
vi.mock('@tresjs/core', () => ({
  useTres: () => ({ camera: { value: null } }),
  useLoop: () => ({ onRender: vi.fn(), onBeforeRender: vi.fn() }),
}))

describe('OfficeWorker', () => {
  it('接受 position 与 workerId props', () => {
    const wrapper = mount(OfficeWorker, {
      props: { position: [-3, 0, -2], workerId: 'ai_news' },
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('点击触发 select 事件', async () => {
    const wrapper = mount(OfficeWorker, {
      props: { position: [3, 0, -2], workerId: 'stock' },
    })
    await wrapper.trigger('click')
    expect(wrapper.emitted('select')).toBeTruthy()
  })
})
