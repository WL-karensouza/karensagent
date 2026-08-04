<!-- 评分趋势折线图：展示历史评分变化，用于报告页 score-card 右侧 -->
<script setup>
import { ref, watch, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([LineChart, GridComponent, TooltipComponent, CanvasRenderer])

const props = defineProps({
  points: { type: Array, default: () => [] },
})

const chartRef = ref(null)
let chartInstance = null

/* 格式化时间：MM-DD HH:mm */
function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const M = String(d.getMonth() + 1).padStart(2, '0')
  const D = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const m = String(d.getMinutes()).padStart(2, '0')
  return `${M}-${D} ${h}:${m}`
}

/* 初始化/更新图表 */
function renderChart() {
  if (!chartRef.value) return
  if (!props.points || props.points.length < 2) return

  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
  }

  const times = props.points.map(p => formatTime(p.created_at))
  const scores = props.points.map(p => p.score)

  chartInstance.setOption({
    grid: {
      top: 8,
      right: 8,
      bottom: 18,
      left: 32,
    },
    xAxis: {
      type: 'category',
      data: times,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        color: '#A8A29E',
        fontSize: 10,
        interval: Math.max(Math.floor(times.length / 3), 0),
      },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      splitNumber: 3,
      axisLabel: {
        color: '#A8A29E',
        fontSize: 10,
      },
      splitLine: {
        lineStyle: { color: '#F0EBE4', type: 'dashed' },
      },
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#fff',
      borderColor: '#E8E3DA',
      textStyle: { color: '#2D2A26', fontSize: 12 },
      formatter: (params) => {
        const p = params[0]
        return `${p.axisValue}<br/>评分：<b>${p.value}</b> / 100`
      },
    },
    series: [{
      type: 'line',
      data: scores,
      smooth: true,
      symbol: 'circle',
      symbolSize: 4,
      lineStyle: { color: '#D97706', width: 2 },
      itemStyle: { color: '#D97706' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(217,119,6,0.12)' },
          { offset: 1, color: 'rgba(217,119,6,0.01)' },
        ]),
      },
    }],
  }, true)
}

watch(() => props.points, () => {
  nextTick(() => renderChart())
}, { deep: true })

onUnmounted(() => {
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})
</script>

<template>
  <div class="trend-chart-wrapper">
    <!-- 数据不足时显示提示文案 -->
    <div v-if="!points || points.length < 2" class="trend-empty">
      首次报告，无历史趋势
    </div>
    <!-- 图表容器 -->
    <div v-show="points && points.length >= 2" ref="chartRef" class="trend-chart"></div>
  </div>
</template>

<style scoped>
/* 趋势图外层容器：适配 score-card 右侧空白，限制最大宽度防挤压 */
.trend-chart-wrapper {
  flex: 1;
  min-width: 260px;
  max-width: 420px;
  height: 150px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 图表画布：填满容器 */
.trend-chart {
  width: 100%;
  height: 100%;
}

/* 无历史数据提示：浅色小字居中 */
.trend-empty {
  font-size: 0.78rem;
  color: var(--text-muted, #A8A29E);
  text-align: center;
  user-select: none;
}
</style>