<script setup>
/* ═══════════════════════════════════════════
   OfficeRoom —— 房间结构：灯光系统 + 地板 + 墙体 + 窗户
   浅色国际配色，阴影 / 抗锯齿由 TresCanvas 统一开启
   ═══════════════════════════════════════════ */
</script>

<template>
  <TresGroup>
    <!-- ══ 灯光系统 ══ -->
    <!-- 环境光：基础照明，避免死黑 -->
    <TresAmbientLight :intensity="0.6" />
    <!-- 半球光：天空白 / 地面暖木色，柔和过渡 -->
    <TresHemisphereLight :intensity="0.4" color="#ffffff" ground-color="#E8D5B7" />
    <!-- 主方向光：模拟窗外阳光，场景中唯一产生阴影的光源 -->
    <TresDirectionalLight
      :position="[6, 11, 7]"
      :intensity="1.4"
      color="#fff4e0"
      cast-shadow
      :shadow-mapSize-width="2048"
      :shadow-mapSize-height="2048"
      :shadow-camera-left="-10"
      :shadow-camera-right="10"
      :shadow-camera-top="10"
      :shadow-camera-bottom="-10"
      :shadow-camera-near="0.5"
      :shadow-camera-far="40"
      :shadow-bias="-0.0004"
    />
    <!-- 暖色顶灯：增加室内氛围（物理光照单位，decay 衰减） -->
    <TresPointLight :position="[0, 4.2, 0]" :intensity="6" color="#ffd9a0" :distance="16" :decay="2" />

    <!-- ══ 地板（浅木色，接收阴影） ══ -->
    <TresMesh :rotation="[-Math.PI / 2, 0, 0]" receive-shadow>
      <TresPlaneGeometry :args="[14, 10]" />
      <TresMeshStandardMaterial color="#E8D5B7" :roughness="0.85" :metalness="0.05" />
    </TresMesh>

    <!-- ══ 后墙 ══ -->
    <TresMesh :position="[0, 2.5, -5]" receive-shadow>
      <TresPlaneGeometry :args="[14, 5]" />
      <TresMeshStandardMaterial color="#F2EFE9" :roughness="0.95" />
    </TresMesh>

    <!-- ══ 侧墙（半高，留出俯视空间方便观察） ══ -->
    <TresMesh :rotation="[0, Math.PI / 2, 0]" :position="[-7, 1.25, 0]" receive-shadow>
      <TresPlaneGeometry :args="[10, 2.5]" />
      <TresMeshStandardMaterial color="#EDE8DF" :roughness="0.95" />
    </TresMesh>
    <TresMesh :rotation="[0, -Math.PI / 2, 0]" :position="[7, 1.25, 0]" receive-shadow>
      <TresPlaneGeometry :args="[10, 2.5]" />
      <TresMeshStandardMaterial color="#EDE8DF" :roughness="0.95" />
    </TresMesh>

    <!-- ══ 后墙发光窗户 ×2（纯装饰，模拟采光） ══ -->
    <TresMesh :position="[-4, 2.6, -4.95]">
      <TresPlaneGeometry :args="[2, 1.6]" />
      <TresMeshBasicMaterial color="#cfe8ff" />
    </TresMesh>
    <TresMesh :position="[4, 2.6, -4.95]">
      <TresPlaneGeometry :args="[2, 1.6]" />
      <TresMeshBasicMaterial color="#cfe8ff" />
    </TresMesh>
  </TresGroup>
</template>
