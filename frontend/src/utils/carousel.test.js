import { describe, it, expect } from 'vitest'
import { slideDotCount } from './carousel.js'

describe('slideDotCount（自选股轮播指示点数）', () => {
  it('5 只股一屏 3 张 → 3 个点（与左右按钮步数一一对应）', () => {
    expect(slideDotCount(5, 3)).toBe(3)
  })

  it('4 只股一屏 3 张 → 2 个点', () => {
    expect(slideDotCount(4, 3)).toBe(2)
  })

  it('恰好一屏（3 只）→ 1 个点', () => {
    expect(slideDotCount(3, 3)).toBe(1)
  })

  it('空自选股 → 兜底 1 个点（导航区本身不显示）', () => {
    expect(slideDotCount(0, 3)).toBe(1)
  })
})
