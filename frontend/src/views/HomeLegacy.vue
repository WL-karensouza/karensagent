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
      <!-- AI 新闻 Agent -->
      <div class="agent-card" @click="openAgent('ai_news')">
        <div class="agent-card-header">
          <div class="agent-icon" style="background:#0d6efd;">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 6v6l4 2"/>
            </svg>
          </div>
          <div class="agent-status">
            <span class="status-dot running"></span>
            运行中
          </div>
        </div>

        <div class="agent-card-body">
          <h3>AI 前沿速递</h3>
          <p class="agent-desc">每日 Tavily 搜索 + DeepSeek 智能摘要，自动推送 AI 行业新闻到飞书</p>

          <div class="agent-stats">
            <div class="agent-stat-item">
              <span class="agent-stat-value">{{ store.stats.today_daily || 0 }}</span>
              <span class="agent-stat-label">今日日报</span>
            </div>
            <div class="agent-stat-item">
              <span class="agent-stat-value">{{ store.stats.today_weekly || 0 }}</span>
              <span class="agent-stat-label">今日周报</span>
            </div>
            <div class="agent-stat-item">
              <span class="agent-stat-value">{{ store.stats.week_reports || 0 }}</span>
              <span class="agent-stat-label">近一周报告</span>
            </div>
          </div>

          <div class="agent-meta">
            <span class="meta-tag">每天 09:00 推送</span>
            <span class="meta-tag">飞书</span>
            <span class="meta-tag">Tavily + DeepSeek</span>
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
