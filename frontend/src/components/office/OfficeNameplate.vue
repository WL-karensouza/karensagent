<script setup>
/* ═══════════════════════════════════════════
   OfficeNameplate —— 地面工位名牌
   Canvas 绘制文字 → CanvasTexture，平铺于地面
   文字与 stores/agent.js 的 label 保持一致
   ═══════════════════════════════════════════ */
import * as THREE from 'three'
import { computed } from 'vue'

const props = defineProps({
  /* 名牌位置 [x, y, z] */
  position: { type: Array, default: () => [0, 0.02, 0] },
  /* 名牌文字（AI 前沿 / 股票分析） */
  text: { type: String, default: '' },
})

/* 点击名牌 → 上抛 select，OfficeScene 据此跳转对应工位 */
const emit = defineEmits(['select'])

/* 绘制名牌贴图 */
function createNameplateTexture(text) {
  const canvas = document.createElement('canvas')
  canvas.width = 512
  canvas.height = 200
  const ctx = canvas.getContext('2d')

  // 浅色底
  ctx.fillStyle = '#F5F1E8'
  ctx.fillRect(0, 0, 512, 200)
  // 主题橙边框
  ctx.strokeStyle = '#D97706'
  ctx.lineWidth = 12
  ctx.strokeRect(10, 10, 492, 180)

  // 文字
  ctx.fillStyle = '#2A2E35'
  ctx.font = 'bold 76px "Microsoft YaHei", sans-serif'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(text, 256, 108)

  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  texture.needsUpdate = true
  return texture
}

const plateTexture = computed(() => createNameplateTexture(props.text))
</script>

<template>
  <!-- 扁平名牌，平躺于地面、文字朝上（MeshBasicMaterial 保证清晰可读） -->
  <!-- @click：点击名牌进入对应工位（TresJS 射线点击） -->
  <TresMesh :position="position" :rotation="[-Math.PI / 2, 0, 0]" receive-shadow @click="emit('select')">
    <TresPlaneGeometry :args="[1.1, 0.44]" />
    <TresMeshBasicMaterial :map="plateTexture" />
  </TresMesh>
</template>
