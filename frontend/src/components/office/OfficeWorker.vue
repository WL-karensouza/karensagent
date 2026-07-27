<script setup>
/* ═══════════════════════════════════════════
   OfficeWorker —— 工作人员（V1 几何体占位 + 打字动画 + 交互）
   坐姿：躯干 / 头 / 双臂（枢轴打字）/ 大腿小腿
   交互：悬浮放大 1.05× + pointer 光标；点击上抛 select 事件
   主题色随 workerId 区分（呼应平台配色）
   ═══════════════════════════════════════════ */
import { ref, computed } from 'vue'
import { useWorkerAnimation } from '../../composables/useWorkerAnimation'

const props = defineProps({
  /* 工位位置 [x, y, z]（与对应办公桌一致） */
  position: { type: Array, default: () => [0, 0, 0] },
  /* Agent id：ai_news | stock */
  workerId: { type: String, default: 'ai_news' },
})

/* 点击上抛给 OfficeScene，本组件不碰 router */
const emit = defineEmits(['select'])

/* 衬衫主题色：AI 前沿橙 / 股票分析深蓝 */
const shirt = computed(() => (props.workerId === 'stock' ? '#1E3A8A' : '#D97706'))
const SKIN = '#F0C8A8'
const PANTS = '#3A3E45'

/* 手臂枢轴分组 ref → 交给打字动画驱动 */
const leftArm = ref(null)
const rightArm = ref(null)
useWorkerAnimation(leftArm, rightArm)

/* ══ 交互：悬浮缩放 + 光标 + 点击 ══ */
const hovered = ref(false)
function onOver() {
  hovered.value = true
  document.body.style.cursor = 'pointer'
}
function onOut() {
  hovered.value = false
  document.body.style.cursor = 'auto'
}
function onClick() {
  emit('select', props.workerId)
}
</script>

<template>
  <!-- 根分组：承载整体悬浮缩放与指针事件（事件从子 mesh 冒泡上来） -->
  <TresGroup
    :position="position"
    :scale="hovered ? [1.05, 1.05, 1.05] : [1, 1, 1]"
    @click="onClick"
    @pointer-over="onOver"
    @pointer-out="onOut"
  >
    <!-- ══ 躯干（上移+加高：抬高坐姿，腿/脚不动；数值为肉眼验收初值） ══ -->
    <TresMesh :position="[0, 0.86, 0.55]" cast-shadow>
      <TresBoxGeometry :args="[0.3, 0.5, 0.2]" />
      <TresMeshStandardMaterial :color="shirt" :roughness="0.8" />
    </TresMesh>

    <!-- ══ 头部（抬高+略放大，坐姿头顶≈1.38，明显高过桌面与显示器下沿） ══ -->
    <TresMesh :position="[0, 1.24, 0.55]" cast-shadow>
      <TresSphereGeometry :args="[0.14, 20, 20]" />
      <TresMeshStandardMaterial :color="SKIN" :roughness="0.7" />
    </TresMesh>

    <!-- ══ 左臂（肩随躯干上移；枢轴在肩，向前下伸向键盘，打字时绕 x 轴摆动） ══ -->
    <TresGroup ref="leftArm" :position="[-0.19, 1.02, 0.52]">
      <TresMesh :position="[0, -0.1, -0.2]" :rotation="[0.7, 0, 0]" cast-shadow>
        <TresBoxGeometry :args="[0.07, 0.07, 0.4]" />
        <TresMeshStandardMaterial :color="shirt" :roughness="0.8" />
      </TresMesh>
    </TresGroup>

    <!-- ══ 右臂 ══ -->
    <TresGroup ref="rightArm" :position="[0.19, 1.02, 0.52]">
      <TresMesh :position="[0, -0.1, -0.2]" :rotation="[0.7, 0, 0]" cast-shadow>
        <TresBoxGeometry :args="[0.07, 0.07, 0.4]" />
        <TresMeshStandardMaterial :color="shirt" :roughness="0.8" />
      </TresMesh>
    </TresGroup>

    <!-- ══ 大腿（坐姿，水平向前） ══ -->
    <TresMesh :position="[-0.1, 0.48, 0.36]" cast-shadow>
      <TresBoxGeometry :args="[0.1, 0.1, 0.34]" />
      <TresMeshStandardMaterial :color="PANTS" :roughness="0.85" />
    </TresMesh>
    <TresMesh :position="[0.1, 0.48, 0.36]" cast-shadow>
      <TresBoxGeometry :args="[0.1, 0.1, 0.34]" />
      <TresMeshStandardMaterial :color="PANTS" :roughness="0.85" />
    </TresMesh>

    <!-- ══ 小腿（垂直向下） ══ -->
    <TresMesh :position="[-0.1, 0.26, 0.2]" cast-shadow>
      <TresBoxGeometry :args="[0.09, 0.36, 0.09]" />
      <TresMeshStandardMaterial :color="PANTS" :roughness="0.85" />
    </TresMesh>
    <TresMesh :position="[0.1, 0.26, 0.2]" cast-shadow>
      <TresBoxGeometry :args="[0.09, 0.36, 0.09]" />
      <TresMeshStandardMaterial :color="PANTS" :roughness="0.85" />
    </TresMesh>
  </TresGroup>
</template>
