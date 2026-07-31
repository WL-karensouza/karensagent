<!-- PROTOTYPE 变体 B — 长文档式：无卡片，章节标题 + 发丝线分隔，排版驱动的编辑阅读流 -->
<script setup>
import { computed } from 'vue'
import AiPanel from '../AiPanel.vue'
import { dirOf, DIR_SYM, DIR_COLOR, TREND_COLOR, TREND_SYM, ATTR_COLOR, valSym, valColor } from '../mockReport.js'

const props = defineProps({
  report: { type: Object, required: true },
})

/* 小环几何常量（r=34） */
const CIRC = 2 * Math.PI * 34
const offset = computed(() => CIRC * (1 - props.report.score / 100))
/* 判决方向 → 涨红跌绿：小环 + 决策符号同色（仅评分区） */
const dirKey = computed(() => dirOf(props.report.decision))
const verdictColor = computed(() => DIR_COLOR[dirKey.value])
const verdictSym = computed(() => DIR_SYM[dirKey.value])

const trendSym = t => TREND_SYM[t] || '·'
const trendColor = t => TREND_COLOR[t] || 'var(--sent-mid)'
const attrColor = d => ATTR_COLOR[d] || 'var(--sent-mid)'
const levelCls = l => ({ 高: 'lv-strong', 中: 'lv-mid', 低: 'lv-soft' }[l] || 'lv-mid')
</script>

<template>
  <div class="vb-layout">
    <!-- ===== 左列：文档流 ===== -->
    <div class="vb-main">
      <!-- 评分 hero：巨型数字 + 小环 + 单行决策 -->
      <section class="vb-hero">
        <div class="vb-hero-left">
          <div class="vb-score-line">
            <span class="vb-score-num">{{ report.score }}</span>
            <span class="vb-score-unit">/ 100 综合评分</span>
          </div>
          <p class="vb-rating-line">{{ report.rating_sentence }}</p>
          <div class="vb-hero-actions">
            <span class="vb-decision"><span class="vb-ic" :style="{ color: verdictColor }">{{ verdictSym }}</span> {{ report.decision }}</span>
            <button class="vb-link-btn">推送飞书 →</button>
          </div>
        </div>
        <div class="vb-hero-gauge">
          <svg width="84" height="84" viewBox="0 0 84 84">
            <circle cx="42" cy="42" r="34" fill="none" stroke="var(--sent-bg)" stroke-width="8" />
            <circle cx="42" cy="42" r="34" fill="none" :stroke="verdictColor" stroke-width="8"
              stroke-linecap="round" :stroke-dasharray="CIRC" :stroke-dashoffset="offset"
              transform="rotate(-90 42 42)" class="vb-arc" />
          </svg>
        </div>
      </section>
      <div class="vb-hairline" />

      <!-- M1 核心结论 -->
      <section class="vb-mod">
        <header class="vb-mhead">
          <span class="vb-mnum">01</span><h2>核心结论与操作建议</h2><span class="vb-rule" />
        </header>
        <blockquote class="vb-rating">{{ report.rating_sentence }}</blockquote>
        <ul class="vb-logic">
          <li v-for="(p, i) in report.core_logic" :key="i">{{ p }}</li>
        </ul>
        <p class="vb-prices">
          <strong style="color: var(--red)">↑</strong> 支撑位 {{ report.reference_prices.support }}
          <span class="vb-sep">/</span>
          <strong style="color: var(--green)">↓</strong> 压力位 {{ report.reference_prices.resistance }}
        </p>
      </section>

      <!-- M2 公司画像 -->
      <section class="vb-mod">
        <header class="vb-mhead">
          <span class="vb-mnum">02</span><h2>公司画像与估值定位</h2><span class="vb-rule" />
        </header>
        <dl class="vb-defs">
          <div><dt>所属行业</dt><dd>{{ report.company.industry }}</dd></div>
          <div><dt>总市值</dt><dd>{{ report.company.market_cap }}</dd></div>
          <div><dt>PE（TTM）</dt><dd>{{ report.company.pe_ttm }}</dd></div>
          <div><dt>PB</dt><dd>{{ report.company.pb }}</dd></div>
          <div><dt>护城河</dt><dd>{{ report.company.moat }}</dd></div>
          <div><dt>估值水平</dt><dd class="vb-em">{{ report.company.valuation_level }}</dd></div>
        </dl>
      </section>

      <!-- M3 财务健康 -->
      <section class="vb-mod">
        <header class="vb-mhead">
          <span class="vb-mnum">03</span><h2>财务健康状况</h2><span class="vb-rule" />
        </header>
        <ul class="vb-metrics">
          <li v-for="f in report.financial" :key="f.name">
            <span class="vb-metric-name">{{ f.name }}</span>
            <span class="vb-metric-val" :style="{ color: trendColor(f.trend) }">{{ f.value }}</span>
            <span class="vb-metric-trend" :style="{ color: trendColor(f.trend) }">{{ trendSym(f.trend) }}</span>
          </li>
        </ul>
      </section>

      <!-- M4 股价走势与资金 -->
      <section class="vb-mod">
        <header class="vb-mhead">
          <span class="vb-mnum">04</span><h2>股价走势与资金动向</h2><span class="vb-rule" />
        </header>
        <p class="vb-flow">
          近 20 日 <strong :style="{ color: trendColor(report.price.direction) }">{{ report.price.change_20d }} {{ trendSym(report.price.direction) }}</strong>；
          {{ report.price.main_force }}；{{ report.price.margin }}。
        </p>
      </section>

      <!-- M5 北向资金 -->
      <section class="vb-mod">
        <header class="vb-mhead">
          <span class="vb-mnum">05</span><h2>北向资金拆解</h2><span class="vb-rule" />
        </header>
        <p class="vb-flow">
          持仓占比 <strong>{{ report.northbound.holding_ratio }}</strong>，
          5 日变化 <strong :style="{ color: trendColor(report.northbound.direction) }">{{ report.northbound.change_5d }} {{ trendSym(report.northbound.direction) }}</strong>。
          {{ report.northbound.comment }}
        </p>
      </section>

      <!-- M6 股东筹码 -->
      <section class="vb-mod">
        <header class="vb-mhead">
          <span class="vb-mnum">06</span><h2>股东结构与筹码集中度</h2><span class="vb-rule" />
        </header>
        <p class="vb-flow">
          第一大股东 <strong>{{ report.shareholders.top1 }}</strong>，
          筹码集中度 <strong>{{ report.shareholders.concentration }}</strong>，
          流通股东 <strong>{{ report.shareholders.float_holders }}</strong>。
        </p>
      </section>

      <!-- M7 催化舆情 -->
      <section class="vb-mod">
        <header class="vb-mhead">
          <span class="vb-mnum">07</span><h2>催化剂与近期舆情</h2><span class="vb-rule" />
        </header>
        <div class="vb-duo">
          <div class="vb-duo-col positive">
            <h3>▲ 利好催化</h3>
            <ul><li v-for="(c, i) in report.catalysts.positive" :key="i">{{ c }}</li></ul>
          </div>
          <div class="vb-duo-col negative">
            <h3>▼ 利空扰动</h3>
            <ul><li v-for="(c, i) in report.catalysts.negative" :key="i">{{ c }}</li></ul>
          </div>
        </div>
      </section>

      <!-- M8 风险评估 -->
      <section class="vb-mod">
        <header class="vb-mhead">
          <span class="vb-mnum">08</span><h2>风险评估与 ESG 表现</h2><span class="vb-rule" />
        </header>
        <ul class="vb-risks">
          <li v-for="(r, i) in report.risks" :key="i">
            <span class="vb-lv" :class="levelCls(r.level)">{{ r.level }}</span>{{ r.text }}
          </li>
        </ul>
      </section>

      <!-- M9 操作指南 -->
      <section class="vb-mod">
        <header class="vb-mhead">
          <span class="vb-mnum">09</span><h2>散户实战操作指南</h2><span class="vb-rule" />
        </header>
        <dl class="vb-advice">
          <div><dt>买入区间</dt><dd>{{ report.advice.buy }}</dd></div>
          <div><dt>止损纪律</dt><dd>{{ report.advice.stop }}</dd></div>
          <div><dt>止盈目标</dt><dd>{{ report.advice.profit }}</dd></div>
        </dl>
        <p class="vb-tip">{{ report.advice.tip }}</p>
      </section>

      <!-- 信号归因 -->
      <section class="vb-mod">
        <header class="vb-mhead">
          <span class="vb-mnum">SA</span><h2>信号归因</h2><span class="vb-rule" />
        </header>
        <ul class="vb-attr">
          <li v-for="a in report.attribution" :key="a.factor">
            <span class="vb-attr-name">{{ a.factor }}</span>
            <span class="vb-attr-dots" :style="{ color: attrColor(a.direction) }">{{ '■'.repeat(Math.round(a.weight / 10)) }}{{ '□'.repeat(10 - Math.round(a.weight / 10)) }}</span>
            <span class="vb-attr-val" :style="{ color: attrColor(a.direction) }">{{ a.direction }} {{ a.weight }}</span>
          </li>
        </ul>
      </section>

      <!-- 元信息 -->
      <p class="vb-meta">
        生成时间：{{ report.meta.created_at }} ｜ Token：{{ report.meta.token_used }}
      </p>
    </div>

    <!-- ===== 右列：AI 助理（虚线边注风格） ===== -->
    <aside class="vb-side">
      <AiPanel />
    </aside>
  </div>
</template>

<style scoped>
/* ===== 两列骨架（锁定决策） ===== */
.vb-layout { display: flex; gap: 40px; align-items: flex-start; }
.vb-main { flex: 1; min-width: 0; max-width: 792px; }
.vb-side {
  width: 360px;
  flex-shrink: 0;
  position: sticky;
  top: calc(var(--topnav-height, 64px) + 24px);
  max-height: calc(100vh - var(--topnav-height, 64px) - 48px);
  overflow: auto;
}
/* 虚线边注：AI 面板在文档流语境中退居"旁注" */
.vb-side :deep(.ai-panel) { border-style: dashed; }
@media (max-width: 1280px) {
  .vb-layout { flex-direction: column; }
  .vb-main { max-width: 860px; }
  .vb-side { width: 100%; max-width: 860px; position: static; max-height: none; }
}

/* ===== 评分 hero ===== */
.vb-hero {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 32px;
  padding-bottom: 28px;
  animation: vb-fade 0.5s ease both;
}
.vb-score-line { display: flex; align-items: baseline; gap: 14px; }
.vb-score-num {
  font-size: 4.2rem;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
  line-height: 1;
  color: var(--sent-strong);
  letter-spacing: -0.03em;
}
.vb-score-unit { font-size: 0.82rem; color: var(--sent-soft); }
.vb-rating-line {
  margin: 18px 0 0;
  font-size: 1rem;
  color: var(--sent-mid);
  line-height: 1.9;
  max-width: 34em;
}
.vb-hero-actions { display: flex; align-items: center; gap: 16px; margin-top: 18px; }
.vb-decision {
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--sent-strong);
  border-bottom: 2px solid var(--sent-strong);
  padding-bottom: 2px;
}
.vb-link-btn {
  border: none;
  background: none;
  padding: 0;
  font-size: 0.8rem;
  font-family: inherit;
  color: var(--sent-mid);
  cursor: pointer;
  transition: color 0.15s ease;
}
.vb-link-btn:hover { color: var(--sent-strong); }
.vb-hero-gauge { padding-top: 10px; }
.vb-arc { transition: stroke-dashoffset 0.8s cubic-bezier(0.4, 0, 0.2, 1); }
.vb-hairline { height: 1px; background: var(--border-color); margin-bottom: 8px; }

/* ===== 章节头：编号 + 标题 + 发丝线 ===== */
.vb-mod { padding: 26px 0 6px; animation: vb-fade 0.45s ease both; }
.vb-main > .vb-mod:nth-of-type(2) { animation-delay: 0.06s; }
.vb-main > .vb-mod:nth-of-type(3) { animation-delay: 0.12s; }
.vb-main > .vb-mod:nth-of-type(n + 4) { animation-delay: 0.18s; }
@keyframes vb-fade { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
.vb-mhead { display: flex; align-items: baseline; gap: 14px; margin-bottom: 16px; }
.vb-mnum {
  font-size: 0.78rem;
  font-family: 'JetBrains Mono', monospace;
  color: var(--sent-soft);
}
.vb-mhead h2 {
  margin: 0;
  font-size: 1.02rem;
  font-weight: 700;
  color: var(--sent-strong);
  letter-spacing: 0.01em;
}
.vb-rule { flex: 1; height: 1px; background: var(--border-color); align-self: center; }

/* ===== M1 ===== */
.vb-rating {
  margin: 0;
  padding: 2px 0;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--sent-strong);
  line-height: 1.9;
}
.vb-logic { margin: 16px 0 0; padding-left: 20px; }
.vb-logic li { font-size: 0.86rem; color: var(--sent-mid); margin: 8px 0; line-height: 1.8; }
.vb-prices { margin: 16px 0 0; font-size: 0.84rem; color: var(--sent-mid); }
.vb-prices strong { color: var(--sent-strong); font-weight: 700; margin-right: 4px; }
.vb-sep { margin: 0 12px; color: var(--sent-soft); }

/* ===== M2 定义列表 ===== */
.vb-defs {
  margin: 0;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0 32px;
}
.vb-defs > div {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-color);
}
.vb-defs dt { font-size: 0.78rem; color: var(--sent-soft); }
.vb-defs dd { margin: 0; font-size: 0.88rem; font-weight: 600; color: var(--sent-strong); }
.vb-em { border-bottom: 2px solid var(--sent-strong); }

/* ===== M3 指标行 ===== */
.vb-metrics { margin: 0; padding: 0; list-style: none; }
.vb-metrics li {
  display: flex;
  align-items: baseline;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-color);
}
.vb-metrics li:last-child { border-bottom: none; }
.vb-metric-name { flex: 1; font-size: 0.84rem; color: var(--sent-mid); }
.vb-metric-val {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.92rem;
  font-weight: 600;
  color: var(--sent-strong);
  margin-right: 16px;
}
.vb-metric-trend { font-weight: 700; color: var(--sent-strong); }

/* ===== 叙述段落（M4/M5/M6） ===== */
.vb-flow { margin: 0; font-size: 0.88rem; color: var(--sent-mid); line-height: 2; }
.vb-flow strong { color: var(--sent-strong); font-weight: 700; }

/* ===== M7 两栏 ===== */
.vb-duo { display: grid; grid-template-columns: 1fr 1fr; }
.vb-duo-col { padding: 0 20px; }
.vb-duo-col:first-child { padding-left: 0; border-right: 1px solid var(--border-color); }
.vb-duo-col:last-child { padding-right: 0; }
.vb-duo-col h3 { margin: 0 0 10px; font-size: 0.8rem; font-weight: 700; color: var(--sent-strong); }
.vb-duo-col ul { margin: 0; padding-left: 16px; }
.vb-duo-col li { font-size: 0.82rem; color: var(--sent-mid); line-height: 1.8; }
/* 利好/利空整列按涨红跌绿上色 */
.vb-duo-col.positive h3, .vb-duo-col.positive li { color: var(--red); }
.vb-duo-col.negative h3, .vb-duo-col.negative li { color: var(--green); }

/* ===== M8 风险 ===== */
.vb-risks { margin: 0; padding: 0; list-style: none; }
.vb-risks li {
  padding: 10px 0;
  border-bottom: 1px solid var(--border-color);
  font-size: 0.86rem;
  color: var(--sent-mid);
  line-height: 1.7;
}
.vb-risks li:last-child { border-bottom: none; }
.vb-lv {
  display: inline-block;
  min-width: 2.2em;
  text-align: center;
  margin-right: 12px;
  font-size: 0.7rem;
  font-weight: 700;
  padding: 2px 6px;
  border: 1px solid var(--border-color);
  border-radius: 3px;
}
.lv-strong { color: var(--sent-strong); border-color: var(--sent-strong); }
.lv-mid { color: var(--sent-mid); }
.lv-soft { color: var(--sent-soft); }

/* ===== M9 ===== */
.vb-advice { margin: 0; display: flex; flex-direction: column; }
.vb-advice > div {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 11px 0;
  border-bottom: 1px solid var(--border-color);
}
.vb-advice dt { font-size: 0.78rem; color: var(--sent-soft); }
.vb-advice dd {
  margin: 0;
  font-size: 0.86rem;
  font-weight: 700;
  color: var(--sent-strong);
  font-family: 'JetBrains Mono', monospace;
}
.vb-tip { margin: 14px 0 0; font-size: 0.8rem; color: var(--sent-mid); line-height: 1.8; }

/* ===== 信号归因：字符条形 ===== */
.vb-attr { margin: 0; padding: 0; list-style: none; }
.vb-attr li { display: flex; align-items: baseline; gap: 14px; padding: 7px 0; }
.vb-attr-name { width: 76px; font-size: 0.8rem; color: var(--sent-mid); }
.vb-attr-dots {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.72rem;
  letter-spacing: 2px;
  color: var(--sent-strong);
}
.vb-attr-val {
  margin-left: auto;
  font-size: 0.76rem;
  font-family: 'JetBrains Mono', monospace;
  color: var(--sent-mid);
}

/* ===== 元信息 ===== */
.vb-meta { margin: 20px 0 24px; font-size: 0.76rem; color: var(--sent-soft); }
</style>
