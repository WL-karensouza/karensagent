<!--
  PROTOTYPE — 投研报告页改版原型（验证完即删）
  问题：在已锁定决策（中性黑白灰 / 两列布局 / 右侧 sticky AI 面板）前提下，
        报告模块的视觉形态选哪种。三个结构不同的变体经 ?variant=A|B|C 切换：
        A 卡片模块式 / B 长文档式 / C 高密度财报式
-->
<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { mockReport } from './mockReport.js'
import PrototypeSwitcher from '../../components/PrototypeSwitcher.vue'
import VariantA from './variants/VariantA.vue'
import VariantB from './variants/VariantB.vue'
import VariantC from './variants/VariantC.vue'

const VARIANTS = [
  { key: 'A', name: '卡片模块式' },
  { key: 'B', name: '长文档式' },
  { key: 'C', name: '高密度财报式' },
]
const COMPONENTS = { A: VariantA, B: VariantB, C: VariantC }

const route = useRoute()
/* 非法 variant 值回落到 A */
const variant = computed(() => {
  const v = route.query.variant
  return COMPONENTS[v] ? String(v) : 'A'
})
</script>

<template>
  <div class="rp-root">
    <!-- 页头（锁定决策：返回按钮 + 标题置于整页顶部、全宽，不塞进左列） -->
    <div class="rp-head">
      <button class="rp-back">← 返回仪表盘</button>
      <h1 class="rp-title">
        {{ mockReport.meta.stock_name }}（{{ mockReport.meta.stock_code }}）投研报告
      </h1>
    </div>

    <!-- 当前变体：两列内容区 -->
    <component :is="COMPONENTS[variant]" :report="mockReport" />

    <!-- 原型切换条 -->
    <PrototypeSwitcher :variants="VARIANTS" />
  </div>
</template>

<style scoped>
/* 原型根容器：中性灰阶 token 在此定义（验证通过后迁入 style.css :root） */
.rp-root {
  --sent-strong: #2D2A26; /* 强调：近黑 */
  --sent-mid: #8B857B;    /* 中间：暖中灰 */
  --sent-soft: #B9B2A6;   /* 弱化：暖浅灰 */
  --sent-bg: #F4F1EB;     /* 中性块底 */
}

/* 页头 */
.rp-back {
  display: inline-block;
  margin-bottom: 16px;
  border: none;
  background: none;
  padding: 0;
  color: var(--sent-mid);
  font-size: 0.82rem;
  font-family: inherit;
  cursor: pointer;
  transition: color 0.15s ease;
}
.rp-back:hover { color: var(--sent-strong); }
.rp-title {
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--sent-strong);
  margin: 0 0 24px;
  letter-spacing: 0.01em;
}
</style>
