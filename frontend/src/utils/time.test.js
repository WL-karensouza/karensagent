import { describe, it, expect } from 'vitest'
import { formatChatTime } from './time.js'

describe('formatChatTime', () => {
  const now = new Date(2026, 7, 7, 14, 30) // 2026-08-07 14:30

  it('今天的消息显示 时:分', () => {
    expect(formatChatTime('2026-08-07T11:14:00', now)).toBe('11:14')
    expect(formatChatTime(new Date(2026, 7, 7, 0, 5), now)).toBe('00:05')
  })

  it('其他日子只显示 月-日', () => {
    expect(formatChatTime('2026-08-06T13:14:00', now)).toBe('08-06')
    expect(formatChatTime('2026-01-03T08:00:00', now)).toBe('01-03')
  })

  it('数据库空格格式（MySQL 返回形态）同样可解析', () => {
    expect(formatChatTime('2026-08-07 11:04:00', now)).toBe('11:04')
    expect(formatChatTime('2026-08-06 12:50:00', now)).toBe('08-06')
  })

  it('空值 / 非法值返回空串', () => {
    expect(formatChatTime(null, now)).toBe('')
    expect(formatChatTime(undefined, now)).toBe('')
    expect(formatChatTime('', now)).toBe('')
    expect(formatChatTime('not-a-date', now)).toBe('')
  })
})
