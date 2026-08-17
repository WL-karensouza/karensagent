<script setup>
/* ═══════════════════════════════════════════
   OfficeHome —— V1 新首页（3D 办公室）
   职责：WebGL 可用性检测 / 加载 spinner / 降级入口
   唯一的路由出口：场景组件只抛事件，路由跳转集中在此
   ═══════════════════════════════════════════ */
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import OfficeScene from '../components/office/OfficeScene.vue'

const router = useRouter()
const ready = ref(false)
const webglOk = ref(true)
const showHint = ref(false)
let hintTimer = null

/* 唯一的路由出口：场景抛 go-agent 事件 → 这里跳转 */
function goAgent(id) {
  router.push(`/agent/${id}`)
}
function onSceneReady() {
  ready.value = true
  /* 场景就绪后浮现操作提示，5 秒后自动淡出 */
  showHint.value = true
  hintTimer = setTimeout(() => {
    showHint.value = false
  }, 5000)
}

onUnmounted(() => {
  if (hintTimer) clearTimeout(hintTimer)
})

/* WebGL 可用性检测，不可用时降级为 HTML 入口卡片 */
onMounted(() => {
  try {
    const canvas = document.createElement('canvas')
    webglOk.value = !!(canvas.getContext('webgl2') || canvas.getContext('webgl'))
  } catch {
    webglOk.value = false
  }
})
</script>

<template>
  <div class="office-home">
    <!-- WebGL 不可用：降级为纯 HTML 入口 -->
    <div v-if="!webglOk" class="webgl-fallback">
      <p>当前浏览器不支持 3D 渲染，请通过下方入口访问：</p>
      <div class="fallback-links">
        <button class="btn btn-primary" @click="goAgent('ai_news')">AI 前沿</button>
        <button class="btn btn-primary" @click="goAgent('stock')">股票分析</button>
      </div>
    </div>

    <!-- 正常路径：3D 场景 -->
    <template v-else>
      <Transition name="fade">
        <div v-if="!ready" class="loading-fallback">
          <div class="spinner" />
          <p>加载 3D 场景中...</p>
        </div>
      </Transition>
      <OfficeScene @ready="onSceneReady" @go-agent="goAgent" />

      <!-- 操作提示：场景就绪后浮现，数秒自动淡出 -->
      <Transition name="fade">
        <div v-if="showHint" class="scene-hint">🖱️ 拖动旋转 · 滚轮缩放 · 点击工位进入</div>
      </Transition>
    </template>
  </div>
</template>

<style scoped>
/* ══ 全屏 3D 容器 ══
   position:fixed 挣脱 .main-content 的 1280px 居中与 padding 约束，
   top 取 --topnav-height 自动避让 TopNav（首页无子导航时为 64px） */
.office-home {
  position: fixed;
  inset: 0;
  top: var(--topnav-height, 64px);
}

/* ══ 加载占位 ══ */
.loading-fallback {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--text-muted);
  font-size: 0.9rem;
}

/* ══ WebGL 降级入口 ══ */
.webgl-fallback {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 20px;
  color: var(--text-secondary);
}
.fallback-links {
  display: flex;
  gap: 16px;
}

/* ══ 操作提示浮层（浅色半透明胶囊，自动淡出） ══ */
.scene-hint {
  position: absolute;
  left: 50%;
  bottom: 28px;
  transform: translateX(-50%);
  padding: 8px 18px;
  background: rgba(255, 255, 255, 0.88);
  color: var(--text-secondary);
  font-size: 0.85rem;
  border-radius: 999px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  pointer-events: none;
  backdrop-filter: blur(4px);
}

/* ══ spinner 淡入淡出 ══ */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
