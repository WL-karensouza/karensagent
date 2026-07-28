<script setup>
/* ═══════════════════════════════════════════
   OfficeDesk —— 单个办公工位（复用两次）
   双轨制：优先加载 glTF 工位模型（桌+显示器+键鼠+座椅+台灯小物），
   加载失败自动降级为原几何体组合，场景永不白屏
   props.theme：降级模式下决定主题点缀色（呼应平台配色）
   ═══════════════════════════════════════════ */
import { computed } from 'vue'
import GltfModel from './GltfModel.vue'

const props = defineProps({
  /* 工位位置 [x, y, z] */
  position: { type: Array, default: () => [0, 0, 0] },
  /* 主题：ai_news（橙） | stock（深蓝） */
  theme: { type: String, default: 'ai_news' },
})

/* 主题点缀色：AI 前沿用平台橙，股票分析用深蓝（仅降级模式使用） */
const accent = computed(() => (props.theme === 'stock' ? '#1E3A8A' : '#D97706'))

/* 模型朝向：绕 Y 轴 +90°，把模型侧置的椅子转到正前方（对齐工人 +z 坐标），
   并让坐姿者面朝后墙大屏（呼应原始构图与"盯盘"主题）。方向不对时改此角度（90° 步进） */
const deskRotation = [0, Math.PI / 2, 0]

/* 椅子与桌子拉开的间距（世界米）。模型内椅子是独立节点，沿模型本地 -x 平移，
   经外层 +90° 旋转后正好落在世界 +z（朝工人/镜头方向），从而拉开椅桌间距。
   方向反了就把下面的减号改加号；值调小=椅子往桌靠(前移)，调大=拉远。0.25 为前移后的值 */
const chairGap = 0.25

/* 归一化后的场景微调：把椅子节点沿"离桌方向"挪出 chairGap */
function prepareWorkstation(scene) {
  const scale = scene.scale.x || 1
  const chair = findNodeByName(scene, 'Chair')
  if (chair) chair.position.x -= chairGap / scale
}

/* 按关键字模糊匹配节点（traverse 父先于子，命中父节点 Chair.003 而非其网格子级） */
function findNodeByName(root, keyword) {
  let hit = null
  root.traverse((node) => {
    if (!hit && node.name?.includes(keyword)) hit = node
  })
  return hit
}

/* 四根桌腿的平面坐标（降级模式） */
const legs = [
  [-0.78, -0.35],
  [0.78, -0.35],
  [-0.78, 0.35],
  [0.78, 0.35],
]
</script>

<template>
  <!-- glTF 工位模型：整体放大（size 调大→桌子变大），+90° 摆正朝向；xz 居中+落地+阴影由 GltfModel 自动处理 -->
  <GltfModel
    src="/models/furniture/desk_workstation.glb"
    :size="3.5"
    :rotation="deskRotation"
    :prepare="prepareWorkstation"
    :position="position"
  >
    <!-- 加载失败兜底：原几何体工位（桌面+饰条+桌腿+显示器+键盘+椅子） -->
    <template #fallback>
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
    </template>
  </GltfModel>
</template>
