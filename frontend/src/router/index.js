import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('../views/OfficeHome.vue'),
    meta: { title: 'Agent 控制台', noPageTransition: true },
  },

  /* ── AI 新闻 Agent ── */
  {
    path: '/agent/ai_news',
    component: () => import('../views/agent/AiNewsDashboard.vue'),
    meta: { agent: 'ai_news', title: 'AI 前沿 · 仪表盘' },
  },
  {
    path: '/agent/ai_news/history',
    component: () => import('../views/agent/AiNewsHistory.vue'),
    meta: { agent: 'ai_news', title: 'AI 前沿 · 推送历史' },
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
