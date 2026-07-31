import { describe, it, expect } from 'vitest'
import {
  scoreColor, decisionBadge,
  dirOf, verdictColor, verdictSym,
  trendColor, trendSym, attrColor, valSym, valColor,
} from './stock.js'

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

describe('dirOf', () => {
  it('看多/偏多 → up', () => {
    expect(dirOf('谨慎看多')).toBe('up')
    expect(dirOf('强烈看多')).toBe('up')
    expect(dirOf('偏多')).toBe('up')
  })
  it('看空/偏空 → down', () => {
    expect(dirOf('看空')).toBe('down')
    expect(dirOf('谨慎看空')).toBe('down')
  })
  it('中性/空值 → flat', () => {
    expect(dirOf('观望')).toBe('flat')
    expect(dirOf('中性')).toBe('flat')
    expect(dirOf('')).toBe('flat')
    expect(dirOf(null)).toBe('flat')
  })
})

describe('verdictColor / verdictSym（涨红跌绿，灰中性）', () => {
  it('看多 → 红 + ▲', () => {
    expect(verdictColor('谨慎看多')).toBe('var(--red)')
    expect(verdictSym('谨慎看多')).toBe('▲')
  })
  it('看空 → 绿 + ▼', () => {
    expect(verdictColor('看空')).toBe('var(--green)')
    expect(verdictSym('看空')).toBe('▼')
  })
  it('中性 → 灰 + ●', () => {
    expect(verdictColor('观望')).toBe('var(--sent-mid)')
    expect(verdictSym('观望')).toBe('●')
  })
})

describe('trendColor / trendSym', () => {
  it('up → 红 + ↑', () => {
    expect(trendColor('up')).toBe('var(--red)')
    expect(trendSym('up')).toBe('↑')
  })
  it('down → 绿 + ↓', () => {
    expect(trendColor('down')).toBe('var(--green)')
    expect(trendSym('down')).toBe('↓')
  })
  it('flat/未知 → 灰 + ·', () => {
    expect(trendColor('flat')).toBe('var(--sent-mid)')
    expect(trendSym('flat')).toBe('·')
    expect(trendSym('xxx')).toBe('·')
  })
})

describe('attrColor', () => {
  it('偏多红 / 偏空绿 / 中性灰', () => {
    expect(attrColor('偏多')).toBe('var(--red)')
    expect(attrColor('偏空')).toBe('var(--green)')
    expect(attrColor('中性')).toBe('var(--sent-mid)')
  })
})

describe('valSym / valColor（估值：低好红↑、高坏绿↓、合理灰·）', () => {
  it('低 → ↑ 红', () => {
    expect(valSym('低')).toBe('↑')
    expect(valColor('低')).toBe('var(--red)')
  })
  it('合理 → · 灰', () => {
    expect(valSym('合理')).toBe('·')
    expect(valColor('合理')).toBe('var(--sent-mid)')
  })
  it('偏高 → ↓ 绿；极高 → ↓↓ 绿', () => {
    expect(valSym('偏高')).toBe('↓')
    expect(valColor('偏高')).toBe('var(--green)')
    expect(valSym('极高')).toBe('↓↓')
    expect(valColor('极高')).toBe('var(--green)')
  })
})
