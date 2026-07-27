<script setup>
/* ═══════════════════════════════════════════
   OfficeDecorations —— 装饰物
   地毯 / 绿植 / 咖啡机 / 白板 / 书架
   ═══════════════════════════════════════════ */
</script>

<template>
  <TresGroup>
    <!-- ══ 地毯（两工位下方暖色区域） ══ -->
    <TresMesh :rotation="[-Math.PI / 2, 0, 0]" :position="[0, 0.01, -1.5]" receive-shadow>
      <TresPlaneGeometry :args="[9, 4]" />
      <TresMeshStandardMaterial color="#E0CBA8" :roughness="0.95" />
    </TresMesh>

    <!-- ══ 绿植（左后角） ══ -->
    <TresGroup :position="[-6, 0, -4]">
      <!-- 花盆 -->
      <TresMesh :position="[0, 0.25, 0]" cast-shadow>
        <TresCylinderGeometry :args="[0.28, 0.22, 0.5, 16]" />
        <TresMeshStandardMaterial color="#C07850" :roughness="0.8" />
      </TresMesh>
      <!-- 叶簇（数个绿球堆叠） -->
      <TresMesh :position="[0, 0.85, 0]" cast-shadow>
        <TresSphereGeometry :args="[0.42, 16, 16]" />
        <TresMeshStandardMaterial color="#6FA86B" :roughness="0.9" />
      </TresMesh>
      <TresMesh :position="[0.22, 1.1, 0.1]" cast-shadow>
        <TresSphereGeometry :args="[0.28, 16, 16]" />
        <TresMeshStandardMaterial color="#7CB877" :roughness="0.9" />
      </TresMesh>
      <TresMesh :position="[-0.2, 1.05, -0.08]" cast-shadow>
        <TresSphereGeometry :args="[0.24, 16, 16]" />
        <TresMeshStandardMaterial color="#5E9A5A" :roughness="0.9" />
      </TresMesh>
    </TresGroup>

    <!-- ══ 咖啡机（右后靠墙） ══ -->
    <TresGroup :position="[5.8, 0, -4.5]">
      <TresMesh :position="[0, 0.5, 0]" cast-shadow>
        <TresBoxGeometry :args="[0.5, 1.0, 0.5]" />
        <TresMeshStandardMaterial color="#5A5E66" :roughness="0.5" :metalness="0.4" />
      </TresMesh>
      <!-- 指示灯（平台橙点缀） -->
      <TresMesh :position="[0, 0.85, 0.26]">
        <TresBoxGeometry :args="[0.3, 0.2, 0.02]" />
        <TresMeshBasicMaterial color="#D97706" />
      </TresMesh>
    </TresGroup>

    <!-- ══ 白板（右侧墙） ══ -->
    <TresMesh :rotation="[0, -Math.PI / 2, 0]" :position="[6.9, 1.6, 1]" cast-shadow>
      <TresBoxGeometry :args="[2.2, 1.3, 0.05]" />
      <TresMeshStandardMaterial color="#FAFAF8" :roughness="0.6" />
    </TresMesh>

    <!-- ══ 书架（左后靠墙） ══ -->
    <TresGroup :position="[-5.5, 0, -4.6]">
      <TresMesh :position="[0, 0.9, 0]" cast-shadow>
        <TresBoxGeometry :args="[1.2, 1.8, 0.35]" />
        <TresMeshStandardMaterial color="#B89B7A" :roughness="0.8" />
      </TresMesh>
      <!-- 几本彩色书（呼应主题色） -->
      <TresMesh :position="[-0.3, 1.4, 0.18]">
        <TresBoxGeometry :args="[0.08, 0.3, 0.02]" />
        <TresMeshStandardMaterial color="#D97706" />
      </TresMesh>
      <TresMesh :position="[-0.15, 1.4, 0.18]">
        <TresBoxGeometry :args="[0.08, 0.3, 0.02]" />
        <TresMeshStandardMaterial color="#1E3A8A" />
      </TresMesh>
      <TresMesh :position="[0, 1.4, 0.18]">
        <TresBoxGeometry :args="[0.08, 0.3, 0.02]" />
        <TresMeshStandardMaterial color="#6FA86B" />
      </TresMesh>
    </TresGroup>
  </TresGroup>
</template>
