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

  it('暴露 walkTo 供 Task 7 会谈调度驱动', () => {
    const wrapper = mount(OfficeWorker, {
      props: { position: [0, 0, 0], workerId: 'ai_news' },
    })
    // defineExpose 拼错会静默失败，这里锁定契约
    expect(wrapper.vm.walkTo).toBeTypeOf('function')
  })

  it('暴露 sitDown 供会谈后回工位坐下', () => {
    const wrapper = mount(OfficeWorker, {
      props: { position: [0, 0, 0], workerId: 'ai_news' },
    })
    // F3 契约：walkTo 透传到达回调，sitDown 由状态机落座
    expect(wrapper.vm.sitDown).toBeTypeOf('function')
  })
})
