<script setup>
import { onMounted, computed } from 'vue'
import { useAgentStore } from '../../stores/agent.js'
import AnimatedClock from '../../components/AnimatedClock.vue'

const store = useAgentStore()

onMounted(() => {
  store.fetchStats()
})

const hasLastPush = computed(() => !!store.stats.last_push)
</script>

<template>
  <div>
    <!-- 统计卡片 -->
    <AnimatedClock style="margin-bottom:16px;" />
    <p style="margin:0 0 16px;color:var(--text-secondary);font-size:0.9rem;text-align:center;">AI 前沿每日定时抓取全球 AI 新闻，智能摘要后推送飞书</p>
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon">📅</div>
        <div class="stat-value">{{ store.stats.today_daily || 0 }}</div>
        <div class="stat-label">今日日报</div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">📊</div>
        <div class="stat-value">{{ store.stats.today_weekly || 0 }}</div>
        <div class="stat-label">今日周报</div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">📰</div>
        <div class="stat-value">{{ store.stats.week_reports || 0 }}</div>
        <div class="stat-label">近一周报告</div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">🕐</div>
        <div class="stat-value" style="font-size:1.2rem;">
          {{ hasLastPush ? store.stats.last_push : '暂无' }}
        </div>
        <div class="stat-label">上次推送时间</div>
      </div>
    </div>

    <!-- 操作区 -->
    <div class="card" style="margin-bottom:24px;">
      <h3 style="margin-bottom:16px;font-size:1rem;">⚡ 快捷操作</h3>
      <div style="display:flex;gap:12px;flex-wrap:wrap;">
        <button
          class="btn btn-outline"
          :disabled="store.loading"
          @click="store.triggerFull()"
        >
          🔍 立即抓取 AI 新闻并推送
        </button>
      </div>
      <div v-if="store.loading" class="loading" style="padding:16px 0 0;">
        <span class="spinner"></span> 执行中...
      </div>
    </div>

    <!-- 系统状态 -->
    <div class="card">
      <h3 style="margin-bottom:16px;font-size:1rem;">📋 系统状态</h3>
      <table class="data-table">
        <thead>
          <tr>
            <th>指标</th>
            <th>状态</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>数据库</td>
            <td><span class="star-badge">✅ 正常</span></td>
          </tr>
          <tr>
            <td>定时任务</td>
            <td><span class="star-badge">⏰ 每天 09:00</span></td>
          </tr>
          <tr>
            <td>搜索服务</td>
            <td><span class="star-badge">🔍 Tavily API</span></td>
          </tr>
          <tr>
            <td>摘要模型</td>
            <td><span class="star-badge">🤖 DeepSeek</span></td>
          </tr>
          <tr>
            <td>推送到</td>
            <td><span class="star-badge">📨 飞书群</span></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}
.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  text-align: center;
  transition: all 0.2s ease;
}
.stat-card:hover {
  box-shadow: var(--shadow-hover);
  border-color: var(--accent);
}
.stat-icon {
  font-size: 1.5rem;
  margin-bottom: 8px;
}
.stat-value {
  font-size: 1.8rem;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}
.stat-label {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-top: 4px;
}
.card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 24px;
}
.data-table {
  width: 100%;
  border-collapse: collapse;
}
.data-table th {
  text-align: left;
  font-size: 0.8rem;
  color: var(--text-muted);
  font-weight: 500;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-light);
}
.data-table td {
  padding: 10px 0;
  font-size: 0.9rem;
  border-bottom: 1px solid var(--border-light);
}
.star-badge {
  font-size: 0.85rem;
  font-weight: 500;
}
.loading {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
  font-size: 0.9rem;
}
.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--border-color);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
