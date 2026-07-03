<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAgentStore } from '../stores/agent.js'

const router = useRouter()
const store = useAgentStore()

onMounted(() => {
  store.fetchStats()
})

function openAgent(id) {
  router.push(`/agent/${id}`)
}
</script>

<template>
  <div>
    <div class="page-header">
      <h1>Agent 控制台</h1>
      <p>管理和监控所有 AI Agent 的运行状态</p>
    </div>

    <!-- Agent 卡片网格 -->
    <div class="agent-card-grid">
      <!-- GitHub Agent -->
      <div class="agent-card" @click="openAgent('github')">
        <div class="agent-card-header">
          <div class="agent-icon" style="background:#24292e;">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="#fff">
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61-.546-1.385-1.335-1.755-1.335-1.755-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 21.795 24 17.295 24 12c0-6.63-5.37-12-12-12z"/>
            </svg>
          </div>
          <div class="agent-status">
            <span class="status-dot running"></span>
            运行中
          </div>
        </div>

        <div class="agent-card-body">
          <h3>GitHub 热榜追踪</h3>
          <p class="agent-desc">每日抓取 GitHub Trending 和 AI 前沿资讯，关键词过滤后推送到飞书</p>

          <div class="agent-stats">
            <div class="agent-stat-item">
              <span class="agent-stat-value">{{ store.stats.today_repos || 0 }}</span>
              <span class="agent-stat-label">今日仓库</span>
            </div>
            <div class="agent-stat-item">
              <span class="agent-stat-value">{{ store.stats.today_news || 0 }}</span>
              <span class="agent-stat-label">今日资讯</span>
            </div>
            <div class="agent-stat-item">
              <span class="agent-stat-value">{{ store.stats.today_pushes || 0 }}</span>
              <span class="agent-stat-label">推送次数</span>
            </div>
          </div>

          <div class="agent-meta">
            <span class="meta-tag">每天 {{ store.stats.push_time || '09:00' }} 推送</span>
            <span class="meta-tag">飞书</span>
          </div>
        </div>
      </div>

      <!-- 股票 Agent -->
      <div class="agent-card agent-card--placeholder" @click="openAgent('stock')">
        <div class="agent-card-header">
          <div class="agent-icon" style="background:#1a1a2e;">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/>
              <polyline points="16 7 22 7 22 13"/>
            </svg>
          </div>
          <div class="agent-status">
            <span class="status-dot idle"></span>
            待开发
          </div>
        </div>

        <div class="agent-card-body">
          <h3>股票分析</h3>
          <p class="agent-desc">AI 驱动的股票市场分析，技术指标解读与趋势预测</p>

          <div class="agent-stats agent-stats--placeholder">
            <div class="agent-stat-item">
              <span class="agent-stat-value">—</span>
              <span class="agent-stat-label">跟踪标的</span>
            </div>
            <div class="agent-stat-item">
              <span class="agent-stat-value">—</span>
              <span class="agent-stat-label">今日信号</span>
            </div>
            <div class="agent-stat-item">
              <span class="agent-stat-value">—</span>
              <span class="agent-stat-label">准确率</span>
            </div>
          </div>

          <div class="agent-meta">
            <span class="meta-tag meta-tag--muted">即将上线</span>
          </div>
        </div>
      </div>

      <!-- 新增 Agent 入口 -->
      <div class="agent-card agent-card--add">
        <div class="agent-card-add-content">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          <span>添加新 Agent</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Agent 卡片网格 */
.agent-card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

/* 单个 Agent 卡片 */
.agent-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  overflow: hidden;
  cursor: pointer;
  transition: all 0.25s ease;
}
.agent-card:hover {
  box-shadow: var(--shadow-hover);
  border-color: var(--accent);
  transform: translateY(-2px);
}

.agent-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 0;
}
.agent-icon {
  width: 44px; height: 44px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
}
.agent-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.78rem;
  color: var(--text-muted);
  font-weight: 500;
}
.status-dot {
  width: 7px; height: 7px;
  border-radius: 50%;
}
.status-dot.running {
  background: #22C55E;
  box-shadow: 0 0 6px rgba(34,197,94,0.4);
}
.status-dot.idle {
  background: var(--text-muted);
}

.agent-card-body {
  padding: 16px 24px 24px;
}
.agent-card-body h3 {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.01em;
}
.agent-desc {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin-top: 6px;
  line-height: 1.5;
}

/* 统计数字 */
.agent-stats {
  display: flex;
  gap: 24px;
  margin-top: 20px;
  padding: 14px 16px;
  background: var(--bg-subtle);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-light);
}
.agent-stat-item {
  display: flex;
  flex-direction: column;
}
.agent-stat-value {
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}
.agent-stat-label {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-top: 2px;
}

.agent-meta {
  display: flex;
  gap: 8px;
  margin-top: 14px;
}
.meta-tag {
  font-size: 0.73rem;
  color: var(--accent);
  background: var(--accent-light);
  padding: 3px 10px;
  border-radius: 999px;
  font-weight: 500;
}
.meta-tag--muted {
  color: var(--text-muted);
  background: var(--bg-hover);
}

/* 占位 Agent 卡片 */
.agent-card--placeholder {
  opacity: 0.7;
}
.agent-card--placeholder:hover {
  opacity: 1;
}
.agent-stats--placeholder .agent-stat-value {
  color: var(--text-muted);
}

/* 添加 Agent 卡片 */
.agent-card--add {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 260px;
  border-style: dashed;
  border-color: var(--border-color);
  background: transparent;
}
.agent-card--add:hover {
  border-color: var(--accent);
  background: var(--bg-subtle);
}
.agent-card-add-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: var(--text-muted);
  font-size: 0.9rem;
  font-weight: 500;
}
.agent-card-add-content svg {
  opacity: 0.4;
}
</style>
