<script setup>
import { computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAgentStore } from '../stores/agent.js'

const router = useRouter()
const route = useRoute()
const store = useAgentStore()

/* 当前激活的 Agent id（从路由路径拆解） */
const activeAgentId = computed(() => {
  const m = route.path.match(/^\/agent\/(\w+)/)
  return m ? m[1] : null
})

/* 是否在首页 */
const isHome = computed(() => route.path === '/')

/* 是否在 Agent 页面 */
const isAgentPage = computed(() => !!route.path.match(/^\/agent\//))

/* 当前 Agent 的子导航项 */
const subNavItems = computed(() => {
  const id = activeAgentId.value
  if (!id) return []
  // 按 agent id 返回对应子导航
  const navMap = {
    github: [
      { label: '仪表盘', to: '/agent/github', exact: true },
      { label: '内容预览', to: '/agent/github/preview' },
      { label: '推送历史', to: '/agent/github/history' },
      { label: '配置管理', to: '/agent/github/settings' },
    ],
    stock: [
      { label: '仪表盘', to: '/agent/stock', exact: true },
      { label: '历史报告', to: '/agent/stock/history' },
      { label: '配置管理', to: '/agent/stock/settings' },
    ],
  }
  return navMap[id] || []
})

/* 动态设置主内容区顶部偏移量，适应子导航高度变化 */
const topnavMainHeight = 64
const topnavSubHeight = 44
function updateLayoutOffset() {
  const hasSub = isAgentPage.value && subNavItems.value.length
  const h = topnavMainHeight + (hasSub ? 1 + topnavSubHeight : 0)
  document.documentElement.style.setProperty('--topnav-height', h + 'px')
}
onMounted(updateLayoutOffset)
watch([isAgentPage, subNavItems], updateLayoutOffset, { immediate: true })

function goAgent(id) {
  router.push(`/agent/${id}`)
}

function goHome() {
  router.push('/')
}

function goSettings() {
  router.push('/settings')
}
</script>

<template>
  <header class="topnav" :class="{ 'has-subnav': isAgentPage && subNavItems.length }">
    <!-- 第一行：主导航 -->
    <div class="topnav-main">
      <!-- 左侧：品牌 -->
      <div class="topnav-brand" @click="goHome">
        <div class="brand-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/>
            <path d="M2 17l10 5 10-5"/>
            <path d="M2 12l10 5 10-5"/>
          </svg>
        </div>
        <span class="brand-name">Karens Agent</span>
      </div>

      <!-- 中间：Agent 标签 -->
      <nav class="topnav-tabs">
        <button
          v-for="agent in store.agents"
          :key="agent.id"
          class="tab-btn"
          :class="{ active: activeAgentId === agent.id }"
          @click="goAgent(agent.id)"
        >
          <svg v-if="agent.id === 'github'" width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61-.546-1.385-1.335-1.755-1.335-1.755-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 21.795 24 17.295 24 12c0-6.63-5.37-12-12-12z"/>
          </svg>
          <svg v-else-if="agent.id === 'stock'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/>
            <polyline points="16 7 22 7 22 13"/>
          </svg>
          <span>{{ agent.label }}</span>
          <span v-if="agent.badge" class="tab-badge">●</span>
        </button>

        <!-- 新增 Agent 按钮 -->
        <button class="tab-btn tab-add" title="添加新 Agent">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
        </button>
      </nav>

      <!-- 右侧：全局操作 -->
      <div class="topnav-actions">
        <button
          class="action-btn"
          :class="{ active: route.path === '/settings' }"
          @click="goSettings"
          title="平台设置"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="3"/>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- 第二行：子导航 -->
    <template v-if="isAgentPage && subNavItems.length">
      <div class="topnav-divider"></div>
      <nav class="topnav-sub">
        <router-link
          v-for="item in subNavItems"
          :key="item.to"
          :to="item.to"
          class="subnav-link"
          :exact="item.exact ?? false"
        >
          {{ item.label }}
        </router-link>
      </nav>
    </template>
  </header>
</template>

<style scoped>
.topnav {
  position: fixed;
  top: 0; left: 0; right: 0;
  z-index: 100;
  background: var(--bg-page);
  border-bottom: 1px solid var(--border-color);
}

/* ── 第一行：主导航 ── */
.topnav-main {
  display: flex;
  align-items: center;
  height: 64px;
  padding: 0 24px;
  gap: 32px;
}

/* ── 分隔线 ── */
.topnav-divider {
  height: 1px;
  background: var(--border-color);
  margin: 0 24px;
}

/* ── 第二行：子导航 ── */
.topnav-sub {
  display: flex;
  align-items: center;
  height: 44px;
  padding: 0 24px;
  gap: 4px;
}
.subnav-link {
  display: inline-flex;
  align-items: center;
  padding: 6px 16px;
  border-radius: var(--radius-md);
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--text-secondary);
  text-decoration: none;
  white-space: nowrap;
  transition: all 0.2s ease;
  position: relative;
}
.subnav-link:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}
.subnav-link.router-link-active {
  color: var(--text-primary);
  font-weight: 600;
}
.subnav-link.router-link-active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 12px; right: 12px;
  height: 2px;
  background: var(--accent);
  border-radius: 1px;
}

/* ── 品牌区 ── */
.topnav-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
  flex-shrink: 0;
}
.brand-icon {
  width: 32px; height: 32px;
  background: var(--accent);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}
.brand-name {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.01em;
}

/* ── Agent 标签区 ── */
.topnav-tabs {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 1;
  overflow-x: auto;
}
.tab-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 8px 16px;
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-secondary);
  background: transparent;
  border: none;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s ease;
  font-family: inherit;
  position: relative;
}
.tab-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}
.tab-btn.active {
  color: var(--text-primary);
  font-weight: 600;
}
.tab-btn.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 12px; right: 12px;
  height: 2px;
  background: var(--accent);
  border-radius: 1px;
}
.tab-add {
  color: var(--text-muted);
  padding: 8px 10px;
  margin-left: 8px;
}
.tab-add:hover {
  color: var(--accent);
}
.tab-badge {
  color: var(--green);
  font-size: 0.5rem;
  margin-left: -2px;
}

/* ── 右侧 ── */
.topnav-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.action-btn {
  width: 36px; height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
}
.action-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}
.action-btn.active {
  color: var(--text-primary);
}
</style>
