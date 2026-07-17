<!-- SVG 环形评分仪表盘（方案4） -->
<script setup>
import { computed } from 'vue'

const props = defineProps({
  score: { type: Number, required: true },
  size: { type: Number, default: 140 },
})

const radius = computed(() => (props.size - 14) / 2)
const circumference = computed(() => 2 * Math.PI * radius.value)
const offset = computed(() => circumference.value * (1 - props.score / 100))
const viewBoxStr = computed(() => `0 0 ${props.size} ${props.size}`)
const center = computed(() => props.size / 2)
const transformStr = computed(() => `rotate(-90 ${center.value} ${center.value})`)

/* 渐变色：红(<40) → 黄(40-70) → 绿(>70) */
const gaugeColor = computed(() => {
  const s = props.score
  if (s < 40) return '#Ef4444'
  if (s < 70) return '#F59E0B'
  return '#10B981'
})
</script>

<template>
  <div class="gauge" :style="{ width: size + 'px', height: size + 'px' }">
    <svg :width="size" :height="size" :viewBox="viewBoxStr">
      <!-- 背景圆环 -->
      <circle
        :cx="center" :cy="center" :r="radius"
        fill="none"
        stroke="var(--bg-hover, #e5e7eb)"
        :stroke-width="10"
      />
      <!-- 评分圆环 -->
      <circle
        :cx="center" :cy="center" :r="radius"
        fill="none"
        :stroke="gaugeColor"
        :stroke-width="10"
        stroke-linecap="round"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="offset"
        :transform="transformStr"
        class="gauge-arc"
      />
    </svg>
    <!-- 中心数字 -->
    <div class="gauge-center">
      <span class="gauge-num" :style="{ color: gaugeColor }">{{ score }}</span>
      <span class="gauge-unit">/100</span>
    </div>
  </div>
</template>

<style scoped>
.gauge {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.gauge-arc {
  transition: stroke-dashoffset 0.8s cubic-bezier(0.4, 0, 0.2, 1);
}
.gauge-center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
}
.gauge-num {
  font-size: 2rem;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
  line-height: 1;
}
.gauge-unit {
  font-size: 0.7rem;
  color: var(--text-muted, #9ca3af);
}
</style>
