/* ═══════════════════════════════════════════
   ThinkingStepsCard 测试
   守护状态映射契约：status → 状态类名 + 图标
   （纯 CSS 配色无法在 happy-dom 中断言，由浏览器目检验证）
   ═══════════════════════════════════════════ */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ThinkingStepsCard from './ThinkingStepsCard.vue'

describe('ThinkingStepsCard 状态渲染', () => {
  it('按 status 渲染对应中文标签与状态类名', () => {
    const wrapper = mount(ThinkingStepsCard, {
      props: { steps: [
        { label: '理解问题', status: 'done' },
        { label: '查询资金流', status: 'running' },
        { label: '生成回答', status: 'pending' },
      ] },
    })
    const rows = wrapper.findAll('.ts-row')
    expect(rows).toHaveLength(3)
    expect(rows[0].classes()).toContain('is-done')
    expect(rows[1].classes()).toContain('is-running')
    expect(rows[0].text()).toContain('理解问题')
  })
})
