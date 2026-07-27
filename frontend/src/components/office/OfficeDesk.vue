<script setup>
/* ═══════════════════════════════════════════
   OfficeDesk —— 单个办公桌（复用两次）
   桌面 + 桌腿 + 显示器 + 键盘 + 椅子
   props.theme 决定主题点缀色（呼应平台配色）
   ═══════════════════════════════════════════ */
import { computed } from 'vue'

const props = defineProps({
  /* 工位位置 [x, y, z] */
  position: { type: Array, default: () => [0, 0, 0] },
  /* 主题：ai_news（橙） | stock（深蓝） */
  theme: { type: String, default: 'ai_news' },
})

/* 主题点缀色：AI 前沿用平台橙，股票分析用深蓝 */
const accent = computed(() => (props.theme === 'stock' ? '#1E3A8A' : '#D97706'))

/* 四根桌腿的平面坐标 */
const legs = [
  [-0.78, -0.35],
  [0.78, -0.35],
  [-0.78, 0.35],
  [0.78, 0.35],
]
</script>

<template>
  <TresGroup :position="position">
    <!-- ══ 桌面 ══ -->
    <TresMesh :position="[0, 0.75, 0]" cast-shadow receive-shadow>
      <TresBoxGeometry :args="[1.7, 0.08, 0.85]" />
      <TresMeshStandardMaterial color="#D9BFA0" :roughness="0.7" :metalness="0.05" />
    </TresMesh>
    <!-- 桌面前沿主题色饰条 -->
    <TresMesh :position="[0, 0.79, 0.42]">
      <TresBoxGeometry :args="[1.7, 0.02, 0.03]" />
      <TresMeshStandardMaterial :color="accent" :roughness="0.5" />
    </TresMesh>

    <!-- ══ 桌腿 ×4（金属） ══ -->
    <TresMesh v-for="(p, i) in legs" :key="i" :position="[p[0], 0.375, p[1]]" cast-shadow>
      <TresBoxGeometry :args="[0.06, 0.75, 0.06]" />
      <TresMeshStandardMaterial color="#B8BCC2" :roughness="0.4" :metalness="0.8" />
    </TresMesh>

    <!-- ══ 显示器 ══ -->
    <!-- 支架 -->
    <TresMesh :position="[0, 0.92, -0.2]" cast-shadow>
      <TresBoxGeometry :args="[0.06, 0.28, 0.06]" />
      <TresMeshStandardMaterial color="#3A3E45" :roughness="0.5" :metalness="0.6" />
    </TresMesh>
    <!-- 屏幕外壳 -->
    <TresMesh :position="[0, 1.18, -0.22]" cast-shadow>
      <TresBoxGeometry :args="[0.72, 0.44, 0.04]" />
      <TresMeshStandardMaterial color="#2A2E35" :roughness="0.5" :metalness="0.4" />
    </TresMesh>
    <!-- 屏幕发光面（朝向坐姿者，主题色微光） -->
    <TresMesh :position="[0, 1.18, -0.195]">
      <TresPlaneGeometry :args="[0.66, 0.38]" />
      <TresMeshBasicMaterial :color="accent" />
    </TresMesh>

    <!-- ══ 键盘 ══ -->
    <TresMesh :position="[0, 0.8, 0.12]" cast-shadow>
      <TresBoxGeometry :args="[0.42, 0.02, 0.15]" />
      <TresMeshStandardMaterial color="#C8CCD2" :roughness="0.5" :metalness="0.3" />
    </TresMesh>

    <!-- ══ 椅子 ══ -->
    <!-- 座垫 -->
    <TresMesh :position="[0, 0.46, 0.55]" cast-shadow>
      <TresBoxGeometry :args="[0.45, 0.08, 0.45]" />
      <TresMeshStandardMaterial color="#4A4E57" :roughness="0.8" />
    </TresMesh>
    <!-- 靠背 -->
    <TresMesh :position="[0, 0.72, 0.76]" cast-shadow>
      <TresBoxGeometry :args="[0.45, 0.5, 0.06]" />
      <TresMeshStandardMaterial color="#4A4E57" :roughness="0.8" />
    </TresMesh>
    <!-- 气压杆 -->
    <TresMesh :position="[0, 0.28, 0.55]" cast-shadow>
      <TresCylinderGeometry :args="[0.03, 0.03, 0.36, 12]" />
      <TresMeshStandardMaterial color="#8A8E95" :roughness="0.3" :metalness="0.9" />
    </TresMesh>
    <!-- 底座 -->
    <TresMesh :position="[0, 0.06, 0.55]" cast-shadow>
      <TresCylinderGeometry :args="[0.28, 0.28, 0.05, 16]" />
      <TresMeshStandardMaterial color="#3A3E45" :roughness="0.4" :metalness="0.7" />
    </TresMesh>
  </TresGroup>
</template>
