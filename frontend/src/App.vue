<script setup>
import { useRoute } from 'vue-router'
import { useAgentStore } from './stores/agent.js'
import TopNav from './components/TopNav.vue'

const store = useAgentStore()
const route = useRoute()
</script>

<template>
  <div class="app-layout">
    <!-- 顶部导航栏 -->
    <TopNav />

    <!-- 主内容区（首页 3D 场景全屏：去掉限宽 / 内边距 / 导航偏移，消除多余滚动条） -->
    <main class="main-content" :class="{ 'is-fullscreen': route.meta.noPageTransition }">
      <router-view v-slot="{ Component }">
        <!-- 首页（3D 场景）禁用全局页面切换动画，其余页面保留 -->
        <transition v-if="!route.meta.noPageTransition" name="page" mode="out-in">
          <component :is="Component" />
        </transition>
        <component v-else :is="Component" />
      </router-view>
    </main>

    <!-- Toast 提示 -->
    <div v-if="store.toast" class="toast">{{ store.toast }}</div>
  </div>
</template>

<style scoped>
/* 全屏页（3D 首页）：覆盖全局 .main-content 的限宽 / 内边距 / 顶部偏移 */
.main-content.is-fullscreen {
  max-width: none;
  padding: 0;
  margin-top: 0;
}

.page-enter-active,
.page-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.page-enter-from {
  opacity: 0;
  transform: translateY(6px);
}
.page-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
