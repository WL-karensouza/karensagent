/**
 * PROTOTYPE — 一次性 mock 数据，验证完即删
 * 字段结构对齐真实 report_json（见 StockReport.vue 各模块取数方式）
 */
export const mockReport = {
  meta: {
    stock_name: '贵州茅台',
    stock_code: '600519',
    created_at: '2026-08-01 09:30',
    token_used: 12840,
  },
  score: 76,
  decision: '谨慎看多',

  /* 模块1：核心结论 */
  rating_sentence: '估值已消化至合理区间，盈利确定性依旧突出，建议逢低分批布局，严守止损纪律。',
  core_logic: [
    '直销占比持续提升，渠道利润结构改善，吨价韧性超预期。',
    '北向资金连续 5 日净买入，筹码向机构集中，浮筹消化充分。',
    '消费税改革预期仍是主要压制项，需跟踪政策落地节奏。',
  ],
  reference_prices: { support: '1,420 元', resistance: '1,580 元' },

  /* 模块2：公司画像 */
  company: {
    industry: '白酒',
    market_cap: '1.91 万亿',
    pe_ttm: '24.6',
    pb: '7.8',
    valuation_level: '合理', // 低 | 合理 | 偏高 | 极高
    moat: '强',
  },

  /* 模块3：财务健康 */
  financial: [
    { name: '营收同比', value: '+16.9%', trend: 'up' },
    { name: '净利同比', value: '+15.0%', trend: 'up' },
    { name: '毛利率', value: '91.5%', trend: 'flat' },
    { name: '资产负债率', value: '20.1%', trend: 'down' },
  ],
  financial_warning: null,

  /* 模块4：股价走势与资金 */
  price: {
    change_20d: '+4.2%',
    direction: 'up',
    main_force: '主力净流入 12.4 亿',
    margin: '两融余额回升 +3.1%',
  },

  /* 模块5：北向资金 */
  northbound: {
    holding_ratio: '6.8%',
    change_5d: '+0.3pt',
    direction: 'up',
    comment: '北向连续 5 日净买入，持仓占比回升，配置型资金态度积极。',
  },

  /* 模块6：股东筹码 */
  shareholders: {
    top1: '茅台集团 54.0%',
    concentration: '提升',
    float_holders: '21.3 万户（-4.2%）',
  },

  /* 模块7：催化舆情 */
  catalysts: {
    positive: ['三期扩产工程竣工，产能释放兑现', '直销占比提升，渠道利润改善'],
    negative: ['白酒行业动销偏弱，批价震荡', '消费降级情绪仍在延续'],
  },

  /* 模块8：风险 */
  risks: [
    { level: '高', text: '消费税改革政策落地节奏与力度不确定' },
    { level: '中', text: '白酒批价下行超预期拖累市场情绪' },
    { level: '低', text: '食品安全事件的尾部风险' },
  ],

  /* 模块9：操作指南 */
  advice: {
    buy: '1,420 – 1,480 元逢低分批',
    stop: '收盘跌破 1,380 元止损',
    profit: '第一目标 1,580 – 1,650 元',
    tip: '仓位建议控制在总仓位 20% 以内，严格执行止损纪律。',
  },

  /* 信号归因 */
  attribution: [
    { factor: '盈利确定性', weight: 82, direction: '偏多' },
    { factor: '资金动向', weight: 71, direction: '偏多' },
    { factor: '估值水平', weight: 64, direction: '中性' },
    { factor: '政策环境', weight: 45, direction: '偏空' },
  ],
}

/* ===== 判决方向 → 涨红跌绿（仅评分区使用；模块内趋势箭头仍走中性） ===== */
export function dirOf(text) {
  if (!text) return 'flat'
  if (/看多|偏多/.test(text)) return 'up'
  if (/看空|偏空/.test(text)) return 'down'
  return 'flat'
}
export const DIR_SYM = { up: '▲', down: '▼', flat: '●' }
/* 复用项目全局语义色：红涨 / 绿跌 / 灰中性 */
export const DIR_COLOR = { up: 'var(--red)', down: 'var(--green)', flat: 'var(--sent-mid)' }

/* 趋势方向（up/down/flat）→ 颜色 / 箭头，供全报告方向符号统一上色 */
export const TREND_COLOR = { up: 'var(--red)', down: 'var(--green)', flat: 'var(--sent-mid)' }
export const TREND_SYM = { up: '↑', down: '↓', flat: '·' }
/* 归因方向（偏多/偏空/中性）→ 颜色 */
export const ATTR_COLOR = { 偏多: 'var(--red)', 偏空: 'var(--green)', 中性: 'var(--sent-mid)' }

/* 估值水平 → 方向符号 / 颜色：低估值=利好红↑，高估值=利空绿↓，合理=中性灰· */
export function valSym(v) {
  return ({ 低: '↑', 偏高: '↓', 极高: '↓↓' })[v] || '·'
}
export function valColor(v) {
  return ({ 低: 'var(--red)', 偏高: 'var(--green)', 极高: 'var(--green)' })[v] || 'var(--sent-mid)'
}
