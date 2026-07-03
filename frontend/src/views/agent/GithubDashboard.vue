<script setup>
import { onMounted, computed } from 'vue'
import { useAgentStore } from '../../stores/agent.js'
import AnimatedClock from '../../components/AnimatedClock.vue'

const store = useAgentStore()

onMounted(() => {
  store.fetchDashboard()
})

const hasLastPush = computed(() => !!store.stats.last_push)
</script>

<template>
  <div>
    <!-- 统计卡片 -->
    <AnimatedClock style="margin-bottom:16px;" />
    <p style="margin:0 0 16px;color:var(--text-secondary);font-size:0.9rem;text-align:center;">GitHub 热榜推送系统运行概览</p>
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon">📥</div>
        <div class="stat-value">{{ store.stats.today_repos }}</div>
        <div class="stat-label">今日抓取仓库</div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">📦</div>
        <div class="stat-value" style="color:var(--text-secondary);">—</div>
        <div class="stat-label">本周不重复仓库</div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">📰</div>
        <div class="stat-value">{{ store.stats.week_news }}</div>
        <div class="stat-label">本周 AI 资讯</div>
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
          @click="store.triggerAction('push')"
        >
          立即推送
        </button>
        <button
          class="btn btn-outline"
          :disabled="store.loading"
          @click="store.triggerAction('full')"
        >
          立即抓取新数据并推送
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
            <td>飞书推送</td>
            <td>
              <span :class="['tag', store.webhooks.configured ? 'active' : '']">
                {{ store.webhooks.configured ? '✅ 已配置' : '⚠️ 未配置' }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
