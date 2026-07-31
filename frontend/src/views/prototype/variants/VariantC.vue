<!-- PROTOTYPE 变体 C — 高密度财报式：表格主导、等宽数字、双栏网格，信息密度优先 -->
<script setup>
import { computed } from 'vue'
import AiPanel from '../AiPanel.vue'
import { dirOf, DIR_SYM, DIR_COLOR, TREND_COLOR, TREND_SYM, ATTR_COLOR, valSym, valColor } from '../mockReport.js'

const props = defineProps({
  report: { type: Object, required: true },
})

/* 评分分段条：10 段，实心段数 = score / 10 */
const filled = computed(() => Math.round(props.report.score / 10))
/* 判决方向 → 涨红跌绿：分段条 + 决策符号同色（仅评分区） */
const dirKey = computed(() => dirOf(props.report.decision))
const verdictColor = computed(() => DIR_COLOR[dirKey.value])
const verdictSym = computed(() => DIR_SYM[dirKey.value])

const trendSym = t => TREND_SYM[t] || '·'
const trendColor = t => TREND_COLOR[t] || 'var(--sent-mid)'
const attrColor = d => ATTR_COLOR[d] || 'var(--sent-mid)'
const levelCls = l => ({ 高: 'lv-strong', 中: 'lv-mid', 低: 'lv-soft' }[l] || 'lv-mid')
</script>

<template>
  <div class="vc-layout">
    <!-- ===== 左列：高密度主体 ===== -->
    <div class="vc-main">
      <!-- 评分数据条：数字 + 分段条 + 决策 -->
      <section class="vc-scorebar">
        <div class="vc-score-num">
          {{ report.score }}<span>/100</span>
        </div>
        <div class="vc-segs" :title="'综合评分 ' + report.score">
          <i v-for="n in 10" :key="n" :style="n <= filled ? { background: verdictColor } : null"></i>
        </div>
        <span class="vc-decision"><span class="vc-ic" :style="{ color: verdictColor }">{{ verdictSym }}</span> {{ report.decision }}</span>
        <button class="vc-btn">推送飞书</button>
      </section>

      <!-- M1 核心结论 -->
      <section class="vc-mod">
        <header class="vc-mhead"><h2>核心结论与操作建议</h2><span class="vc-mtag">M1</span></header>
        <div class="vc-body">
          <p class="vc-rating">{{ report.rating_sentence }}</p>
          <ol class="vc-logic">
            <li v-for="(p, i) in report.core_logic" :key="i">{{ p }}</li>
          </ol>
          <p class="vc-prices">
            支撑 <strong>{{ report.reference_prices.support }}</strong> <span style="color: var(--red)">↑</span>
            <span class="vc-gap">|</span>
            压力 <strong>{{ report.reference_prices.resistance }}</strong> <span style="color: var(--green)">↓</span>
          </p>
        </div>
      </section>

      <!-- M2 + M3 双栏 -->
      <div class="vc-pair">
        <section class="vc-mod">
          <header class="vc-mhead"><h2>公司画像与估值</h2><span class="vc-mtag">M2</span></header>
          <table class="vc-table">
            <tr><td>所属行业</td><td class="vc-v">{{ report.company.industry }}</td></tr>
            <tr><td>总市值</td><td class="vc-v">{{ report.company.market_cap }}</td></tr>
            <tr><td>PE（TTM）</td><td class="vc-v">{{ report.company.pe_ttm }}</td></tr>
            <tr><td>PB</td><td class="vc-v">{{ report.company.pb }}</td></tr>
            <tr><td>护城河</td><td class="vc-v">{{ report.company.moat }}</td></tr>
            <tr><td>估值水平</td><td class="vc-v vc-em">{{ report.company.valuation_level }}</td></tr>
          </table>
        </section>
        <section class="vc-mod">
          <header class="vc-mhead"><h2>财务健康状况</h2><span class="vc-mtag">M3</span></header>
          <table class="vc-table">
            <tr v-for="f in report.financial" :key="f.name">
              <td>{{ f.name }}</td>
              <td class="vc-v" :style="{ color: trendColor(f.trend) }">{{ f.value }}</td>
              <td class="vc-trend" :style="{ color: trendColor(f.trend) }">{{ trendSym(f.trend) }}</td>
            </tr>
            <tr><td colspan="3" class="vc-placeholder">— 预警项：无 —</td></tr>
          </table>
        </section>
      </div>

      <!-- M4 + M5 双栏 -->
      <div class="vc-pair">
        <section class="vc-mod">
          <header class="vc-mhead"><h2>股价走势与资金</h2><span class="vc-mtag">M4</span></header>
          <table class="vc-table">
            <tr><td>20 日涨跌幅</td><td class="vc-v" :style="{ color: trendColor(report.price.direction) }">{{ report.price.change_20d }} {{ trendSym(report.price.direction) }}</td></tr>
            <tr><td>主力资金</td><td class="vc-v">{{ report.price.main_force }}</td></tr>
            <tr><td>两融动态</td><td class="vc-v">{{ report.price.margin }}</td></tr>
          </table>
        </section>
        <section class="vc-mod">
          <header class="vc-mhead"><h2>北向资金拆解</h2><span class="vc-mtag">M5</span></header>
          <table class="vc-table">
            <tr><td>持仓占比</td><td class="vc-v">{{ report.northbound.holding_ratio }}</td></tr>
            <tr><td>5 日变化</td><td class="vc-v" :style="{ color: trendColor(report.northbound.direction) }">{{ report.northbound.change_5d }} {{ trendSym(report.northbound.direction) }}</td></tr>
          </table>
          <p class="vc-note">{{ report.northbound.comment }}</p>
        </section>
      </div>

      <!-- M6 股东筹码 -->
      <section class="vc-mod">
        <header class="vc-mhead"><h2>股东结构与筹码集中度</h2><span class="vc-mtag">M6</span></header>
        <table class="vc-table vc-table-3">
          <tr>
            <td>第一大股东</td><td class="vc-v">{{ report.shareholders.top1 }}</td>
            <td>筹码集中度</td><td class="vc-v">{{ report.shareholders.concentration }}</td>
            <td>流通股东</td><td class="vc-v">{{ report.shareholders.float_holders }}</td>
          </tr>
        </table>
      </section>

      <!-- M7 催化舆情 -->
      <section class="vc-mod">
        <header class="vc-mhead"><h2>催化剂与近期舆情</h2><span class="vc-mtag">M7</span></header>
        <div class="vc-duo">
          <div class="vc-duo-col positive">
            <h3>▲ 利好催化</h3>
            <ul><li v-for="(c, i) in report.catalysts.positive" :key="i">{{ c }}</li></ul>
          </div>
          <div class="vc-duo-col negative">
            <h3>▼ 利空扰动</h3>
            <ul><li v-for="(c, i) in report.catalysts.negative" :key="i">{{ c }}</li></ul>
          </div>
        </div>
      </section>

      <!-- M8 风险 -->
      <section class="vc-mod">
        <header class="vc-mhead"><h2>风险评估与 ESG 表现</h2><span class="vc-mtag">M8</span></header>
        <table class="vc-table">
          <tr v-for="(r, i) in report.risks" :key="i">
            <td class="vc-lv-td"><span class="vc-lv" :class="levelCls(r.level)">{{ r.level }}</span></td>
            <td>{{ r.text }}</td>
          </tr>
        </table>
      </section>

      <!-- M9 操作指南 -->
      <section class="vc-mod">
        <header class="vc-mhead"><h2>散户实战操作指南</h2><span class="vc-mtag">M9</span></header>
        <table class="vc-table">
          <tr><td class="vc-k">买入区间</td><td class="vc-v">{{ report.advice.buy }}</td></tr>
          <tr><td class="vc-k">止损纪律</td><td class="vc-v">{{ report.advice.stop }}</td></tr>
          <tr><td class="vc-k">止盈目标</td><td class="vc-v">{{ report.advice.profit }}</td></tr>
        </table>
        <p class="vc-tip">※ {{ report.advice.tip }}</p>
      </section>

      <!-- 信号归因 -->
      <section class="vc-mod">
        <header class="vc-mhead"><h2>信号归因</h2><span class="vc-mtag">SA</span></header>
        <table class="vc-table vc-attr">
          <tr v-for="a in report.attribution" :key="a.factor">
            <td class="vc-attr-name">{{ a.factor }}</td>
            <td class="vc-attr-barcell">
              <div class="vc-attr-bar" :style="{ width: a.weight + '%', background: attrColor(a.direction) }"></div>
            </td>
            <td class="vc-v vc-attr-w">{{ a.weight }}</td>
            <td class="vc-attr-d" :style="{ color: attrColor(a.direction) }">{{ a.direction }}</td>
          </tr>
        </table>
      </section>

      <!-- 元信息 -->
      <p class="vc-meta">
        生成时间 {{ report.meta.created_at }} ｜ Token {{ report.meta.token_used }}
      </p>
    </div>

    <!-- ===== 右列：AI 助理（sticky 吸附） ===== -->
    <aside class="vc-side">
      <AiPanel />
    </aside>
  </div>
</template>

<style scoped>
/* 高密度基调：更小字号、更紧行高 */
.vc-layout { display: flex; gap: 32px; align-items: flex-start; font-size: 12.5px; }
.vc-main { flex: 1; min-width: 0; max-width: 792px; }
.vc-side {
  width: 360px;
  flex-shrink: 0;
  position: sticky;
  top: calc(var(--topnav-height, 64px) + 24px);
  max-height: calc(100vh - var(--topnav-height, 64px) - 48px);
  overflow: auto;
}
@media (max-width: 1280px) {
  .vc-layout { flex-direction: column; }
  .vc-main { max-width: 860px; }
  .vc-side { width: 100%; max-width: 860px; position: static; max-height: none; }
}

/* ===== 评分数据条 ===== */
.vc-scorebar {
  display: flex;
  align-items: center;
  gap: 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 14px 20px;
  margin-bottom: 14px;
  animation: vc-in 0.4s ease both;
}
.vc-score-num {
  font-size: 1.9rem;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
  color: var(--sent-strong);
  line-height: 1;
}
.vc-score-num span { font-size: 0.72rem; color: var(--sent-soft); margin-left: 4px; }
/* 10 段评分条 */
.vc-segs { display: flex; gap: 4px; flex: 1; }
.vc-segs i { height: 10px; flex: 1; border-radius: 2px; background: var(--sent-bg); }
/* 分段条实心色由内联 style 按涨红跌绿注入，空段沿用基础灰底 */
.vc-decision {
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--sent-strong);
  white-space: nowrap;
}
.vc-btn {
  height: 30px;
  padding: 0 14px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm, 8px);
  background: var(--bg-card);
  font-size: 0.74rem;
  font-family: inherit;
  color: var(--sent-strong);
  cursor: pointer;
  white-space: nowrap;
  transition: border-color 0.15s ease;
}
.vc-btn:hover { border-color: var(--sent-strong); }

/* ===== 模块框：细边框、紧凑标题栏 ===== */
.vc-mod {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: hidden;
  animation: vc-in 0.4s ease both;
}
.vc-pair { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }
.vc-pair .vc-mod { margin-bottom: 0; }
.vc-main > .vc-mod { margin-bottom: 14px; }
.vc-main > :nth-child(2) { animation-delay: 0.04s; }
.vc-main > :nth-child(3) { animation-delay: 0.08s; }
.vc-main > :nth-child(4) { animation-delay: 0.12s; }
.vc-main > :nth-child(n + 5) { animation-delay: 0.16s; }
@keyframes vc-in { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: none; } }
.vc-mhead {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 9px 14px;
  border-bottom: 1px solid var(--border-color);
  background: var(--sent-bg);
}
.vc-mhead h2 {
  margin: 0;
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--sent-strong);
  letter-spacing: 0.03em;
}
.vc-mtag {
  font-size: 0.64rem;
  font-family: 'JetBrains Mono', monospace;
  color: var(--sent-soft);
}
.vc-body { padding: 12px 14px; }

/* ===== M1 ===== */
.vc-rating {
  margin: 0 0 10px;
  font-size: 0.84rem;
  font-weight: 700;
  color: var(--sent-strong);
  line-height: 1.7;
}
.vc-logic { margin: 0; padding-left: 18px; }
.vc-logic li { font-size: 0.78rem; color: var(--sent-mid); margin: 4px 0; line-height: 1.6; }
.vc-prices {
  margin: 10px 0 0;
  padding-top: 8px;
  border-top: 1px dashed var(--border-color);
  font-size: 0.76rem;
  color: var(--sent-mid);
}
.vc-prices strong { font-family: 'JetBrains Mono', monospace; color: var(--sent-strong); }
.vc-gap { margin: 0 10px; color: var(--sent-soft); }

/* ===== 表格 ===== */
.vc-table { width: 100%; border-collapse: collapse; }
.vc-table td {
  padding: 7px 14px;
  font-size: 0.78rem;
  color: var(--sent-mid);
  border-bottom: 1px solid var(--border-color);
  transition: background 0.12s ease;
}
.vc-table tr:last-child td { border-bottom: none; }
.vc-table tr:hover td { background: var(--sent-bg); }
.vc-v {
  text-align: right;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600;
}
.vc-k { width: 72px; color: var(--sent-soft) !important; }
.vc-em { border-bottom: 2px solid var(--sent-strong); }
.vc-trend { width: 30px; text-align: center; font-weight: 700; }
.vc-placeholder { text-align: center; color: var(--sent-soft) !important; font-size: 0.7rem !important; }
.vc-table-3 td { width: auto; }
.vc-note { margin: 0; padding: 8px 14px; font-size: 0.74rem; color: var(--sent-mid); line-height: 1.7; }

/* ===== M7 两栏 ===== */
.vc-duo { display: grid; grid-template-columns: 1fr 1fr; }
.vc-duo-col { padding: 10px 14px; }
.vc-duo-col:first-child { border-right: 1px solid var(--border-color); }
.vc-duo-col h3 { margin: 0 0 6px; font-size: 0.74rem; font-weight: 700; color: var(--sent-strong); }
.vc-duo-col ul { margin: 0; padding-left: 15px; }
.vc-duo-col li { font-size: 0.76rem; color: var(--sent-mid); line-height: 1.7; }
/* 利好/利空整列按涨红跌绿上色 */
.vc-duo-col.positive h3, .vc-duo-col.positive li { color: var(--red); }
.vc-duo-col.negative h3, .vc-duo-col.negative li { color: var(--green); }

/* ===== M8 风险 ===== */
.vc-lv-td { width: 48px; }
.vc-lv {
  display: inline-block;
  width: 2.4em;
  text-align: center;
  font-size: 0.68rem;
  font-weight: 700;
  padding: 1px 0;
  border: 1px solid var(--border-color);
  border-radius: 3px;
}
.lv-strong { color: var(--sent-strong); border-color: var(--sent-strong); }
.lv-mid { color: var(--sent-mid); }
.lv-soft { color: var(--sent-soft); }
.vc-tip {
  margin: 0;
  padding: 8px 14px;
  border-top: 1px dashed var(--border-color);
  font-size: 0.72rem;
  color: var(--sent-mid);
}

/* ===== 信号归因 ===== */
.vc-attr-name { width: 76px; }
.vc-attr-barcell { width: 40%; padding-right: 14px !important; }
.vc-attr-bar { height: 6px; border-radius: 3px; }
/* 归因横条颜色已改由内联 style 注入（偏多红/偏空绿/中性灰） */
.vc-attr-w { width: 36px; }
.vc-attr-d { width: 44px; text-align: right; font-size: 0.72rem !important; }

/* ===== 元信息 ===== */
.vc-meta {
  margin: 4px 0 24px;
  text-align: center;
  font-size: 0.7rem;
  font-family: 'JetBrains Mono', monospace;
  color: var(--sent-soft);
}
</style>
