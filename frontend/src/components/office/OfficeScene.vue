<script setup>
/* ═══════════════════════════════════════════
   OfficeScene —— 3D 场景组合根组件
   组合房间 / 装饰 / 两个工位 / 大屏 / 名牌
   点击名牌 → go-agent（进入工位），场景就绪 → ready
   事件向上抛给 OfficeHome，本组件不直接操作路由
   ═══════════════════════════════════════════ */
import { TresCanvas } from '@tresjs/core'
import { OrbitControls } from '@tresjs/cientos'
import OfficeRoom from './OfficeRoom.vue'
import OfficeDesk from './OfficeDesk.vue'
import OfficeNameplate from './OfficeNameplate.vue'
import OfficeWallScreen from './OfficeWallScreen.vue'
import OfficeDecorations from './OfficeDecorations.vue'
import OfficeCameraClamp from './OfficeCameraClamp.vue'

/* 事件向上抛：go-agent（跳转）/ ready（场景就绪） */
const emit = defineEmits(['go-agent', 'ready'])

function onSceneReady() {
  emit('ready')
}
/* 点击名牌 → 上抛 go-agent，路由跳转交给 OfficeHome */
function onNameplateClick(agentId) {
  emit('go-agent', agentId)
}
</script>

<template>
  <TresCanvas
    shadows
    antialias
    clear-color="#ECE8E0"
    @ready="onSceneReady"
  >
    <!-- 主相机：墙内较高俯视；fov 放宽 + 视线上抬，确保后墙大屏顶部完整入镜（初值肉眼可调） -->
    <TresPerspectiveCamera :position="[0, 4.3, 4.3]" :fov="60" />
    <!-- 轨道控制：左键旋转 / 滚轮缩放；禁用平移防视角歪出房间；不限制 azimuth = 横向 360° -->
    <!-- 距离/角度不做球形限制，统一由 OfficeCameraClamp 夹盒（注：zoom 到边界的抖动属问题2，待架构决策） -->
    <OrbitControls
      :enableDamping="true"
      :enablePan="false"
      :minDistance="2"
      :target="[0, 1.1, -1.6]"
    />

    <OfficeRoom />
    <OfficeDecorations />

    <!-- AI 前沿工位（左侧） → /agent/ai_news -->
    <OfficeDesk :position="[-3, 0, -2]" theme="ai_news" />
    <OfficeNameplate :position="[-3, 0.02, -0.6]" text="AI 前沿" @select="onNameplateClick('ai_news')" />

    <!-- 股票分析工位（右侧） → /agent/stock -->
    <OfficeDesk :position="[3, 0, -2]" theme="stock" />
    <OfficeNameplate :position="[3, 0.02, -0.6]" text="股票分析" @select="onNameplateClick('stock')" />

    <!-- 墙面大屏（静态占位） -->
    <OfficeWallScreen :position="[0, 2.2, -4.8]" />

    <!-- 相机夹盒：每帧把相机位置限制在房间包围盒内，保证视角永不离房间（须排在 OrbitControls 之后注册） -->
    <OfficeCameraClamp />
  </TresCanvas>
</template>

<style scoped>
/* TresCanvas 会填满父容器；父级尺寸由 OfficeHome（Phase 5）提供 */
</style>
