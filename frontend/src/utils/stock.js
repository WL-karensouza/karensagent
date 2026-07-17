/* 股票分析共享工具函数 */

/* ── 分析状态枚举 ── */
export const ANALYSIS_STATE = {
  IDLE: 'idle',
  RUNNING: 'running',
  DONE: 'done',
  PARTIAL: 'partial',
  ERROR: 'error',
}

/* 评分对应的 CSS 颜色变量 */
export function scoreColor(score) {
  if (score >= 70) return 'var(--green)'
  if (score >= 40) return 'var(--accent)'
  return 'var(--red)'
}

/* 投资判断文本加 emoji 前缀 */
export function decisionBadge(d) {
  if (!d) return ''
  if (d.includes('看多')) return '🟢 ' + d
  if (d.includes('看空')) return '🔴 ' + d
  return '🟡 ' + d
}
