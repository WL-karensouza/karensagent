import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('../views/Home.vue'),
    meta: { title: 'Agent 控制台' },
  },

  /* ── GitHub Agent 子路由 ── */
  {
    path: '/agent/github',
    component: () => import('../views/agent/GithubDashboard.vue'),
    meta: { agent: 'github', title: 'GitHub · 仪表盘' },
  },
  {
    path: '/agent/github/preview',
    component: () => import('../views/agent/GithubPreview.vue'),
    meta: { agent: 'github', title: 'GitHub · 内容预览' },
  },
  {
    path: '/agent/github/history',
    component: () => import('../views/agent/GithubHistory.vue'),
    meta: { agent: 'github', title: 'GitHub · 推送历史' },
  },
  {
    path: '/agent/github/settings',
    component: () => import('../views/agent/GithubSettings.vue'),
    meta: { agent: 'github', title: 'GitHub · 配置管理' },
  },

  /* ── 股票 Agent ── */
  {
    path: '/agent/stock',
    component: () => import('../views/agent/StockDashboard.vue'),
    meta: { agent: 'stock', title: '股票分析 · 仪表盘' },
  },
  {
    path: '/agent/stock/report/:id',
    component: () => import('../views/agent/StockReport.vue'),
    meta: { agent: 'stock', title: '股票分析 · 报告详情' },
  },
  {
    path: '/agent/stock/history',
    component: () => import('../views/agent/StockHistory.vue'),
    meta: { agent: 'stock', title: '股票分析 · 历史报告' },
  },
  {
    path: '/agent/stock/settings',
    component: () => import('../views/agent/StockSettings.vue'),
    meta: { agent: 'stock', title: '股票分析 · 配置管理' },
  },

  /* ── 平台全局设置 ── */
  {
    path: '/settings',
    name: 'settings',
    component: () => import('../views/Settings.vue'),
    meta: { title: '平台设置' },
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
