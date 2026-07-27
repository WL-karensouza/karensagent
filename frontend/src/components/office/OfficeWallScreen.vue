<script setup>
/* ═══════════════════════════════════════════
   OfficeWallScreen —— 墙面大屏（V1 静态占位）
   Canvas 2D 绘制占位画面 → CanvasTexture
   V1 内容写死，不读后端、不轮询（真实数据为 V2）
   ═══════════════════════════════════════════ */
import * as THREE from 'three'

defineProps({
  /* 大屏位置 [x, y, z] */
  position: { type: Array, default: () => [0, 2.2, -4.8] },
})

/* 绘制大屏占位画面并生成纹理 */
function createScreenTexture() {
  const canvas = document.createElement('canvas')
  canvas.width = 1024
  canvas.height = 512
  const ctx = canvas.getContext('2d')

  // 深色背景
  ctx.fillStyle = '#0a1628'
  ctx.fillRect(0, 0, 1024, 512)

  // 标题栏
  ctx.fillStyle = '#13233f'
  ctx.fillRect(0, 0, 1024, 84)
  ctx.fillStyle = '#7dd3fc'
  ctx.font = 'bold 40px "Microsoft YaHei", sans-serif'
  ctx.textBaseline = 'middle'
  ctx.fillText('A股板块实时行情', 36, 44)

  // 三列灰色占位条（模拟未来的数据行）
  ctx.fillStyle = '#1e2f4d'
  for (let i = 0; i < 6; i++) {
    const y = 120 + i * 56
    ctx.fillRect(36, y, 300, 32)
    ctx.fillRect(372, y, 220, 32)
    ctx.fillRect(628, y, 360, 32)
  }

  // 底部状态栏
  ctx.fillStyle = '#0f1d33'
  ctx.fillRect(0, 470, 1024, 42)
  ctx.fillStyle = '#5b7290'
  ctx.font = '24px "Microsoft YaHei", sans-serif'
  ctx.fillText('数据加载中...', 36, 492)

  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  texture.needsUpdate = true
  return texture
}

const screenTexture = createScreenTexture()
</script>

<template>
  <TresGroup :position="position">
    <!-- 金属边框 -->
    <TresMesh cast-shadow>
      <TresBoxGeometry :args="[5, 2.7, 0.12]" />
      <TresMeshStandardMaterial color="#2A2E35" :roughness="0.4" :metalness="0.7" />
    </TresMesh>
    <!-- 屏幕画面（MeshBasicMaterial 自发光，不受场景光影响，始终清晰） -->
    <TresMesh :position="[0, 0, 0.07]">
      <TresPlaneGeometry :args="[4.7, 2.4]" />
      <TresMeshBasicMaterial :map="screenTexture" />
    </TresMesh>
  </TresGroup>
</template>
