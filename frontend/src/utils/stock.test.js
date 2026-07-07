import { describe, it, expect } from 'vitest'
import { scoreColor, decisionBadge } from './stock.js'

describe('scoreColor', () => {
  it('score >= 70 返回绿色', () => {
    expect(scoreColor(70)).toBe('var(--green)')
    expect(scoreColor(85)).toBe('var(--green)')
    expect(scoreColor(100)).toBe('var(--green)')
  })

  it('40 <= score < 70 返回 accent 色', () => {
    expect(scoreColor(40)).toBe('var(--accent)')
    expect(scoreColor(55)).toBe('var(--accent)')
    expect(scoreColor(69)).toBe('var(--accent)')
  })

  it('score < 40 返回红色', () => {
    expect(scoreColor(39)).toBe('var(--red)')
    expect(scoreColor(0)).toBe('var(--red)')
    expect(scoreColor(-10)).toBe('var(--red)')
  })
})

describe('decisionBadge', () => {
  it('包含"看多"返回绿色 emoji 前缀', () => {
    expect(decisionBadge('看多')).toBe('🟢 看多')
    expect(decisionBadge('强烈看多')).toBe('🟢 强烈看多')
  })

  it('包含"看空"返回红色 emoji 前缀', () => {
    expect(decisionBadge('看空')).toBe('🔴 看空')
    expect(decisionBadge('谨慎看空')).toBe('🔴 谨慎看空')
  })

  it('其他情况返回黄色 emoji 前缀', () => {
    expect(decisionBadge('观望')).toBe('🟡 观望')
    expect(decisionBadge('中性')).toBe('🟡 中性')
  })

  it('空值返回空字符串', () => {
    expect(decisionBadge(null)).toBe('')
    expect(decisionBadge(undefined)).toBe('')
    expect(decisionBadge('')).toBe('')
  })
})
