<script setup>
/* ═══════════════════════════════════════════
   OfficeCameraClamp —— 相机夹盒约束（纯逻辑组件）
   每帧把相机位置夹在房间包围盒内，保证任意视角都不离房间：
   - 默认 / 旋转 / 缩放时相机永不穿墙
   - 转到小人正面时相机被盒壁推近 → 自然“缓缓放大”看清正面
   约束统一交给“位置夹盒”，不再用 OrbitControls 的球形距离/角度去近似方盒
   须排在 <OrbitControls> 之后注册，使本回调晚于控制器更新执行
   ═══════════════════════════════════════════ */
import { useLoop, useTres } from '@tresjs/core'

/* 房间包围盒：地板 x±7 / z±5、墙高 5；四周留余量防贴墙穿模或瞥见单面墙背面（初值肉眼可调） */
const BOX = { minX: -6.4, maxX: 6.4, minY: 0.5, maxY: 4.6, minZ: -4.4, maxZ: 4.6 }
const clamp = (v, lo, hi) => Math.min(Math.max(v, lo), hi)

/* 相机来自 Tres 上下文（ref）；onRender 仅作为每帧触发器 */
const { camera } = useTres()
const { onRender } = useLoop()

onRender(() => {
  /* 兼容裸 three 对象与 Tres 包装器两种形态 */
  const cam = camera.value?.__tres?.object ?? camera.value
  if (!cam) return
  const p = cam.position
  p.x = clamp(p.x, BOX.minX, BOX.maxX)
  p.y = clamp(p.y, BOX.minY, BOX.maxY)
  p.z = clamp(p.z, BOX.minZ, BOX.maxZ)
})
</script>

<template>
  <!-- 空分组仅承载 setup 的渲染循环副作用，不绘制任何物体 -->
  <TresGroup />
</template>
