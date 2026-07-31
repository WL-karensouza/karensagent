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

/* ── 报告页方向色助手：涨红跌绿，灰中性（仅报告页使用，不动 scoreColor/decisionBadge） ── */
export function dirOf(text) {
  if (!text) return 'flat'
  if (/看多|偏多/.test(text)) return 'up'
  if (/看空|偏空/.test(text)) return 'down'
  return 'flat'
}
/* 决策方向 → 颜色 / 符号 */
export const verdictColor = t => ({ up: 'var(--red)', down: 'var(--green)', flat: 'var(--sent-mid)' })[dirOf(t)]
export const verdictSym = t => ({ up: '▲', down: '▼', flat: '●' })[dirOf(t)]
/* 趋势方向 up/down/flat → 颜色 / 箭头 */
export const trendColor = t => ({ up: 'var(--red)', down: 'var(--green)', flat: 'var(--sent-mid)' })[t] || 'var(--sent-mid)'
export const trendSym = t => ({ up: '↑', down: '↓', flat: '·' })[t] || '·'
/* 归因方向 偏多/偏空/中性 → 颜色 */
export const attrColor = d => ({ 偏多: 'var(--red)', 偏空: 'var(--green)', 中性: 'var(--sent-mid)' })[d] || 'var(--sent-mid)'
/* 估值水平 → 符号 / 颜色 */
export function valSym(v) {
  return ({ 低: '↑', 偏高: '↓', 极高: '↓↓' })[v] || '·'
}
export function valColor(v) {
  return ({ 低: 'var(--red)', 偏高: 'var(--green)', 极高: 'var(--green)' })[v] || 'var(--sent-mid)'
}
/* PE/PB 估值水位 → 符号 / 颜色：偏低=利好红↑，合理=中性灰·，偏高=利空绿↓，极度偏高=绿↓↓ */
export function peLevelSym(v) {
  return ({ 偏低: '↑', 偏高: '↓', 极度偏高: '↓↓' })[v] || '·'
}
export function peLevelColor(v) {
  return ({ 偏低: 'var(--red)', 偏高: 'var(--green)', 极度偏高: 'var(--green)' })[v] || 'var(--sent-mid)'
}
/* 财务趋势文本（中文）→ 颜色：上升/改善=利好红，下滑/恶化=利空绿，其余中性灰 */
export function finTrendColor(t) {
  if (!t) return 'var(--sent-mid)'
  if (/上升|改善/.test(t)) return 'var(--red)'
  if (/下滑|恶化/.test(t)) return 'var(--green)'
  return 'var(--sent-mid)'
}
/* 舆情风向标 → 颜色：偏乐观=红，偏谨慎=绿，中性=灰 */
export function sentimentColor(s) {
  return ({ 偏乐观: 'var(--red)', 偏谨慎: 'var(--green)' })[s] || 'var(--sent-mid)'
}
