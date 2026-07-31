<!-- PROTOTYPE 变体 A — 卡片模块式：每个模块独立白卡，最接近最终落地形态 -->
<script setup>
import { computed } from 'vue'
import AiPanel from '../AiPanel.vue'
import { dirOf, DIR_SYM, DIR_COLOR, TREND_COLOR, TREND_SYM, ATTR_COLOR, valSym, valColor } from '../mockReport.js'

const props = defineProps({
  report: { type: Object, required: true },
})

/* 环形仪表盘几何常量（r=56） */
const CIRC = 2 * Math.PI * 56
const offset = computed(() => CIRC * (1 - props.report.score / 100))
/* 判决方向 → 涨红跌绿：评分环 + 中心数字 + 决策符号同色（仅评分区，模块内箭头仍中性） */
const dirKey = computed(() => dirOf(props.report.decision))
const verdictColor = computed(() => DIR_COLOR[dirKey.value])
const verdictSym = computed(() => DIR_SYM[dirKey.value])

/* 趋势符号 / 颜色：涨红跌绿（模块方向箭头统一上色；M1 支撑压力箭头除外） */
const trendSym = t => TREND_SYM[t] || '·'
const trendColor = t => TREND_COLOR[t] || 'var(--sent-mid)'
const attrColor = d => ATTR_COLOR[d] || 'var(--sent-mid)'
/* 风险等级 → 灰阶档位 */
const levelCls = l => ({ 高: 'lv-strong', 中: 'lv-mid', 低: 'lv-soft' }[l] || 'lv-mid')
/* 归因方向 → 条形灰阶 */
const dirCls = d => ({ 偏多: 'dir-strong', 偏空: 'dir-soft', 中性: 'dir-mid' }[d] || 'dir-mid')
</script>

<template>
  <div class="va-layout">
    <!-- ===== 左列：报告主体 ===== -->
    <div class="va-main">
      <!-- 评分概览卡 -->
      <section class="va-card">
        <div class="va-score">
          <div class="va-gauge">
            <svg width="130" height="130" viewBox="0 0 130 130">
              <circle cx="65" cy="65" r="56" fill="none" stroke="var(--sent-bg)" stroke-width="10" />
              <circle cx="65" cy="65" r="56" fill="none" :stroke="verdictColor" stroke-width="10"
                stroke-linecap="round" :stroke-dasharray="CIRC" :stroke-dashoffset="offset"
                transform="rotate(-90 65 65)" class="va-arc" />
            </svg>
            <div class="va-gauge-center">
              <span class="va-gauge-num" :style="{ color: verdictColor }">{{ report.score }}</span>
              <span class="va-gauge-unit">/100</span>
            </div>
          </div>
          <div class="va-score-info">
            <span class="va-decision"><span class="va-ic" :style="{ color: verdictColor }">{{ verdictSym }}</span> {{ report.decision }}</span>
            <p class="va-score-desc">
              综合评分 <strong>{{ report.score }}</strong> / 100
            </p>
            <button class="va-btn">推送飞书</button>
          </div>
        </div>
      </section>

      <!-- M1 核心结论 -->
      <section class="va-card">
        <header class="va-mhead"><span class="va-mnum">M1</span><h2>核心结论与操作建议</h2></header>
        <blockquote class="va-rating">{{ report.rating_sentence }}</blockquote>
        <ul class="va-logic">
          <li v-for="(p, i) in report.core_logic" :key="i">{{ p }}</li>
        </ul>
        <div class="va-chips">
          <span class="va-chip"><span style="color: var(--red)">↑</span> 支撑位 {{ report.reference_prices.support }}</span>
          <span class="va-chip"><span style="color: var(--green)">↓</span> 压力位 {{ report.reference_prices.resistance }}</span>
        </div>
      </section>

      <!-- M2 公司画像 -->
      <section class="va-card">
        <header class="va-mhead"><span class="va-mnum">M2</span><h2>公司画像与估值定位</h2></header>
        <div class="va-grid">
          <div class="va-kv"><span>所属行业</span><strong>{{ report.company.industry }}</strong></div>
          <div class="va-kv"><span>总市值</span><strong>{{ report.company.market_cap }}</strong></div>
          <div class="va-kv"><span>PE（TTM）</span><strong>{{ report.company.pe_ttm }}</strong></div>
          <div class="va-kv"><span>PB</span><strong>{{ report.company.pb }}</strong></div>
          <div class="va-kv"><span>护城河</span><strong>{{ report.company.moat }}</strong></div>
          <div class="va-kv"><span>估值水平</span><strong class="va-level">{{ report.company.valuation_level }}</strong></div>
        </div>
      </section>

      <!-- M3 财务健康 -->
      <section class="va-card">
        <header class="va-mhead"><span class="va-mnum">M3</span><h2>财务健康状况</h2></header>
        <table class="va-table">
          <tr v-for="f in report.financial" :key="f.name">
            <td>{{ f.name }}</td>
            <td class="va-num" :style="{ color: trendColor(f.trend) }">{{ f.value }}</td>
            <td class="va-trend" :style="{ color: trendColor(f.trend) }">{{ trendSym(f.trend) }}</td>
          </tr>
        </table>
      </section>

      <!-- M4 股价走势与资金 -->
      <section class="va-card">
        <header class="va-mhead"><span class="va-mnum">M4</span><h2>股价走势与资金动向</h2></header>
        <div class="va-stats">
          <div class="va-stat">
            <span>20 日涨跌幅</span>
            <strong :style="{ color: trendColor(report.price.direction) }">{{ report.price.change_20d }} {{ trendSym(report.price.direction) }}</strong>
          </div>
          <div class="va-stat"><span>主力资金</span><strong>{{ report.price.main_force }}</strong></div>
          <div class="va-stat"><span>两融动态</span><strong>{{ report.price.margin }}</strong></div>
        </div>
      </section>

      <!-- M5 北向资金 -->
      <section class="va-card">
        <header class="va-mhead"><span class="va-mnum">M5</span><h2>北向资金拆解</h2></header>
        <div class="va-stats">
          <div class="va-stat"><span>持仓占比</span><strong>{{ report.northbound.holding_ratio }}</strong></div>
          <div class="va-stat">
            <span>5 日变化</span>
            <strong :style="{ color: trendColor(report.northbound.direction) }">{{ report.northbound.change_5d }} {{ trendSym(report.northbound.direction) }}</strong>
          </div>
        </div>
        <p class="va-note">{{ report.northbound.comment }}</p>
      </section>

      <!-- M6 股东筹码 -->
      <section class="va-card">
        <header class="va-mhead"><span class="va-mnum">M6</span><h2>股东结构与筹码集中度</h2></header>
        <div class="va-stats">
          <div class="va-stat"><span>第一大股东</span><strong>{{ report.shareholders.top1 }}</strong></div>
          <div class="va-stat"><span>筹码集中度</span><strong>{{ report.shareholders.concentration }}</strong></div>
          <div class="va-stat"><span>流通股东</span><strong>{{ report.shareholders.float_holders }}</strong></div>
        </div>
      </section>

      <!-- M7 催化舆情 -->
      <section class="va-card">
        <header class="va-mhead"><span class="va-mnum">M7</span><h2>催化剂与近期舆情</h2></header>
        <div class="va-duo">
          <div class="va-duo-col positive">
            <h3>▲ 利好催化</h3>
            <ul><li v-for="(c, i) in report.catalysts.positive" :key="i">{{ c }}</li></ul>
          </div>
          <div class="va-duo-col negative">
            <h3>▼ 利空扰动</h3>
            <ul><li v-for="(c, i) in report.catalysts.negative" :key="i">{{ c }}</li></ul>
          </div>
        </div>
      </section>

      <!-- M8 风险评估 -->
      <section class="va-card">
        <header class="va-mhead"><span class="va-mnum">M8</span><h2>风险评估与 ESG 表现</h2></header>
        <ul class="va-risks">
          <li v-for="(r, i) in report.risks" :key="i">
            <span class="va-lv" :class="levelCls(r.level)">{{ r.level }}</span>
            {{ r.text }}
          </li>
        </ul>
      </section>

      <!-- M9 操作指南 -->
      <section class="va-card">
        <header class="va-mhead"><span class="va-mnum">M9</span><h2>散户实战操作指南</h2></header>
        <div class="va-advice">
          <div class="va-advice-col"><span>买入区间</span><strong>{{ report.advice.buy }}</strong></div>
          <div class="va-advice-col"><span>止损纪律</span><strong>{{ report.advice.stop }}</strong></div>
          <div class="va-advice-col"><span>止盈目标</span><strong>{{ report.advice.profit }}</strong></div>
        </div>
        <p class="va-tip">{{ report.advice.tip }}</p>
      </section>

      <!-- 信号归因 -->
      <section class="va-card">
        <header class="va-mhead"><span class="va-mnum">SA</span><h2>信号归因</h2></header>
        <div class="va-attr">
          <div v-for="a in report.attribution" :key="a.factor" class="va-attr-row">
            <span class="va-attr-name">{{ a.factor }}</span>
            <div class="va-attr-track">
              <div class="va-attr-fill" :style="{ width: a.weight + '%', background: attrColor(a.direction) }"></div>
            </div>
            <span class="va-attr-dir" :style="{ color: attrColor(a.direction) }">{{ a.direction }} {{ a.weight }}</span>
          </div>
        </div>
      </section>

      <!-- 元信息 -->
      <p class="va-meta">
        生成时间：{{ report.meta.created_at }} ｜ Token：{{ report.meta.token_used }}
      </p>
    </div>

    <!-- ===== 右列：AI 助理（sticky 吸附） ===== -->
    <aside class="va-side">
      <AiPanel />
    </aside>
  </div>
</template>

<style scoped>
/* ===== 两列骨架（锁定决策） ===== */
.va-layout { display: flex; gap: 32px; align-items: flex-start; }
.va-main { flex: 1; min-width: 0; max-width: 792px; }
.va-side {
  width: 360px;
  flex-shrink: 0;
  position: sticky;
  top: calc(var(--topnav-height, 64px) + 24px);
  max-height: calc(100vh - var(--topnav-height, 64px) - 48px);
  overflow: auto;
}
/* 窄屏堆叠：与全局 .main-content 断点对齐 */
@media (max-width: 1280px) {
  .va-layout { flex-direction: column; }
  .va-main { max-width: 860px; }
  .va-side { width: 100%; max-width: 860px; position: static; max-height: none; }
}

/* ===== 卡片 ===== */
.va-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 24px 28px;
  margin-bottom: 20px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  animation: va-rise 0.45s ease both;
}
.va-card:hover {
  border-color: var(--sent-soft);
  box-shadow: 0 6px 20px rgba(45, 42, 38, 0.05);
}
/* 错峰入场 */
.va-main > :nth-child(1) { animation-delay: 0s; }
.va-main > :nth-child(2) { animation-delay: 0.05s; }
.va-main > :nth-child(3) { animation-delay: 0.1s; }
.va-main > :nth-child(4) { animation-delay: 0.15s; }
.va-main > :nth-child(5) { animation-delay: 0.2s; }
.va-main > :nth-child(n + 6) { animation-delay: 0.25s; }
@keyframes va-rise {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ===== 卡片头：模块编号徽章 + 标题 ===== */
.va-mhead {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 18px;
}
.va-mnum {
  font-size: 0.68rem;
  font-weight: 600;
  font-family: 'JetBrains Mono', monospace;
  padding: 2px 8px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm, 8px);
  color: var(--sent-mid);
  background: var(--sent-bg);
}
.va-mhead h2 {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--sent-strong);
}

/* ===== 评分概览 ===== */
.va-score { display: flex; align-items: center; gap: 28px; }
.va-gauge { position: relative; width: 130px; height: 130px; flex-shrink: 0; }
.va-arc { transition: stroke-dashoffset 0.8s cubic-bezier(0.4, 0, 0.2, 1); }
.va-gauge-center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.va-gauge-num {
  font-size: 2rem;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
  line-height: 1;
}
.va-gauge-unit { font-size: 0.7rem; color: var(--sent-soft); }
.va-score-info { display: flex; flex-direction: column; gap: 10px; align-items: flex-start; }
.va-decision {
  font-size: 0.82rem;
  font-weight: 700;
  padding: 5px 14px;
  border: 1px solid var(--border-color);
  border-radius: 999px;
  background: var(--sent-bg);
  color: var(--sent-strong);
}
.va-score-desc { margin: 0; font-size: 0.82rem; color: var(--sent-mid); }
.va-score-desc strong { color: var(--sent-strong); }
.va-btn {
  height: 34px;
  padding: 0 18px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  font-size: 0.8rem;
  font-family: inherit;
  color: var(--sent-strong);
  cursor: pointer;
  transition: all 0.15s ease;
}
.va-btn:hover { border-color: var(--sent-strong); }

/* ===== M1 ===== */
.va-rating {
  margin: 0;
  padding: 16px 20px;
  background: var(--sent-bg);
  border-radius: var(--radius-sm, 8px);
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--sent-strong);
  line-height: 1.8;
}
.va-logic { margin: 14px 0 0; padding-left: 20px; }
.va-logic li { font-size: 0.84rem; color: var(--sent-mid); margin: 6px 0; line-height: 1.7; }
.va-chips { display: flex; gap: 12px; margin-top: 14px; flex-wrap: wrap; }
.va-chip {
  font-size: 0.78rem;
  padding: 6px 14px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  color: var(--sent-strong);
  font-weight: 500;
}

/* ===== 通用：键值网格 / 统计行 ===== */
.va-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px 24px; }
.va-kv { display: flex; flex-direction: column; gap: 4px; }
.va-kv span { font-size: 0.74rem; color: var(--sent-soft); }
.va-kv strong { font-size: 0.88rem; color: var(--sent-strong); font-weight: 600; }
.va-level { border-bottom: 2px solid var(--sent-strong); display: inline-block; }
.va-stats { display: flex; gap: 40px; flex-wrap: wrap; }
.va-stat { display: flex; flex-direction: column; gap: 4px; }
.va-stat span { font-size: 0.74rem; color: var(--sent-soft); }
.va-stat strong { font-size: 0.9rem; color: var(--sent-strong); font-weight: 600; }
.va-note { margin: 12px 0 0; font-size: 0.82rem; color: var(--sent-mid); line-height: 1.7; }

/* ===== 表格 ===== */
.va-table { width: 100%; border-collapse: collapse; }
.va-table td {
  padding: 9px 8px;
  font-size: 0.84rem;
  border-bottom: 1px solid var(--border-color);
  color: var(--sent-mid);
}
.va-table tr:last-child td { border-bottom: none; }
.va-num {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600;
  text-align: right;
}
.va-trend { width: 36px; text-align: center; font-weight: 700; }

/* ===== M7 利好/利空两栏 ===== */
.va-duo { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.va-duo-col {
  background: var(--sent-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 14px 16px;
}
.va-duo-col h3 { margin: 0 0 8px; font-size: 0.8rem; font-weight: 700; color: var(--sent-strong); }
.va-duo-col ul { margin: 0; padding-left: 16px; }
.va-duo-col li { font-size: 0.8rem; color: var(--sent-mid); line-height: 1.7; }
/* 利好/利空整列按涨红跌绿上色（标题 + 列表项） */
.va-duo-col.positive h3, .va-duo-col.positive li { color: var(--red); }
.va-duo-col.negative h3, .va-duo-col.negative li { color: var(--green); }

/* ===== M8 风险徽章：三档灰阶 ===== */
.va-risks { margin: 0; padding: 0; list-style: none; }
.va-risks li {
  display: flex;
  align-items: baseline;
  gap: 10px;
  font-size: 0.84rem;
  color: var(--sent-mid);
  padding: 8px 0;
  border-bottom: 1px solid var(--border-color);
  line-height: 1.6;
}
.va-risks li:last-child { border-bottom: none; }
.va-lv {
  flex-shrink: 0;
  font-size: 0.7rem;
  font-weight: 600;
  padding: 2px 10px;
  border-radius: 999px;
  background: var(--sent-bg);
  border: 1px solid var(--border-color);
}
.lv-strong { color: var(--sent-strong); }
.lv-mid { color: var(--sent-mid); }
.lv-soft { color: var(--sent-soft); }

/* ===== M9 操作指南三栏 ===== */
.va-advice { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.va-advice-col {
  background: var(--sent-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.va-advice-col span { font-size: 0.72rem; color: var(--sent-soft); }
.va-advice-col strong { font-size: 0.8rem; color: var(--sent-strong); font-weight: 600; line-height: 1.5; }
.va-tip {
  margin: 12px 0 0;
  padding: 10px 14px;
  background: var(--sent-bg);
  border-radius: var(--radius-md);
  font-size: 0.78rem;
  color: var(--sent-mid);
}

/* ===== 信号归因条形 ===== */
.va-attr-row { display: flex; align-items: center; gap: 12px; padding: 7px 0; }
.va-attr-name { width: 72px; font-size: 0.78rem; color: var(--sent-mid); flex-shrink: 0; }
.va-attr-track { flex: 1; height: 6px; background: var(--sent-bg); border-radius: 3px; overflow: hidden; }
.va-attr-fill { height: 100%; border-radius: 3px; }
/* 归因横条颜色已改由内联 style 注入（偏多红/偏空绿/中性灰） */
.va-attr-dir {
  width: 88px;
  flex-shrink: 0;
  text-align: right;
  font-size: 0.74rem;
  font-family: 'JetBrains Mono', monospace;
  color: var(--sent-mid);
}

/* ===== 元信息 ===== */
.va-meta {
  text-align: center;
  font-size: 0.76rem;
  color: var(--sent-soft);
  padding: 8px 0 24px;
  margin: 0;
}
</style>
