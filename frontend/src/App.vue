<script setup>
import { useAgentStore } from './stores/agent.js'
import TopNav from './components/TopNav.vue'

const store = useAgentStore()
</script>

<template>
  <div class="app-layout">
    <!-- 顶部导航栏 -->
    <TopNav />

    <!-- 主内容区 -->
    <main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <!-- Toast 提示 -->
    <div v-if="store.toast" class="toast">{{ store.toast }}</div>
  </div>
</template>

<style scoped>
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
