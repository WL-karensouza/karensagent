<script setup>
/* ═══════════════════════════════════════════
   OfficeScene —— 3D 场景组合根组件
   组合房间 / 装饰 / 两个工位 / 大屏 / 名牌
   事件向上抛给 OfficeHome，本组件不直接操作路由
   注：工作人员（OfficeWorker）在 Phase 3 接入
   ═══════════════════════════════════════════ */
import { TresCanvas } from '@tresjs/core'
import { OrbitControls } from '@tresjs/cientos'
import OfficeRoom from './OfficeRoom.vue'
import OfficeDesk from './OfficeDesk.vue'
import OfficeWorker from './OfficeWorker.vue'
import OfficeNameplate from './OfficeNameplate.vue'
import OfficeWallScreen from './OfficeWallScreen.vue'
import OfficeDecorations from './OfficeDecorations.vue'

/* 事件向上抛：go-agent（跳转）/ ready（场景就绪） */
const emit = defineEmits(['go-agent', 'ready'])

function onSceneReady() {
  emit('ready')
}
/* 工人点击 → 上抛 go-agent，路由跳转交给 OfficeHome */
function onWorkerClick(agentId) {
  emit('go-agent', agentId)
}
</script>

<template>
  <TresCanvas
    shadows
    antialias
    @ready="onSceneReady"
  >
    <!-- 主相机：v5 必须用子元素声明（:camera prop 只接受相机实例，传配置对象会崩） -->
    <TresPerspectiveCamera :position="[0, 6, 6]" :fov="55" />
    <!-- 轨道控制：左键旋转 / 滚轮缩放 / 右键平移 -->
    <OrbitControls
      :enableDamping="true"
      :minDistance="4"
      :maxDistance="16"
      :maxPolarAngle="Math.PI / 2.5"
      :target="[0, 0, -1]"
    />

    <OfficeRoom />
    <OfficeDecorations />

    <!-- AI 前沿工位（左侧） → /agent/ai_news -->
    <OfficeDesk :position="[-3, 0, -2]" theme="ai_news" />
    <OfficeWorker worker-id="ai_news" :position="[-3, 0, -2]" @select="onWorkerClick" />
    <OfficeNameplate :position="[-3, 0.02, -0.6]" text="AI 前沿" />

    <!-- 股票分析工位（右侧） → /agent/stock -->
    <OfficeDesk :position="[3, 0, -2]" theme="stock" />
    <OfficeWorker worker-id="stock" :position="[3, 0, -2]" @select="onWorkerClick" />
    <OfficeNameplate :position="[3, 0.02, -0.6]" text="股票分析" />

    <!-- 墙面大屏（静态占位） -->
    <OfficeWallScreen :position="[0, 2.2, -4.8]" />
  </TresCanvas>
</template>

<style scoped>
/* TresCanvas 会填满父容器；父级尺寸由 OfficeHome（Phase 5）提供 */
</style>
