/* 聊天消息时间格式化：今天显示时:分，其他日子显示月-日 */

const pad = n => String(n).padStart(2, '0')

/* 入参兼容 ISO 串 / 数据库空格格式 / Date；空或非法返回空串（调用方据此不渲染时间） */
export function formatChatTime(value, now = new Date()) {
  if (!value) return ''
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return ''
  const sameDay = d.getFullYear() === now.getFullYear()
    && d.getMonth() === now.getMonth()
    && d.getDate() === now.getDate()
  return sameDay ? `${pad(d.getHours())}:${pad(d.getMinutes())}` : `${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}
