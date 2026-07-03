<script setup>
import { onMounted } from 'vue'
import { useAgentStore } from '../../stores/agent.js'

const store = useAgentStore()

onMounted(() => {
  store.fetchHistory(30)
})

const platformLabel = (p) => ({ feishu: '飞书' }[p] || p)
const platformIcon = (p) => ({ feishu: '📋' }[p] || '📌')
</script>

<template>
  <div>
    <div class="page-header">
      <h1>推送历史</h1>
      <p>查看所有已发送的推送记录</p>
    </div>

    <div class="card">
      <div v-if="store.pushHistory.length === 0" class="empty-state">
        <div class="empty-icon">📜</div>
        <p>暂无推送历史</p>
      </div>

      <div v-else class="timeline">
        <div
          v-for="item in store.pushHistory"
          :key="item.id"
          class="timeline-item"
        >
          <span
            class="timeline-dot"
            :class="{ failed: item.status === 'failed' }"
          ></span>
          <div class="timeline-content">
            <span class="tl-time">{{ item.push_time }}</span>
            <span class="tl-badge">{{ platformIcon(item.platform) }} {{ platformLabel(item.platform) }}</span>
            <span
              v-if="item.status === 'failed'"
              class="tl-badge"
              style="background:#FEE2E2;color:#DC2626;margin-left:6px;"
            >失败</span>
            <div class="tl-summary">
              {{ item.content_type }} · 仓库 {{ item.repo_count }} · 资讯 {{ item.news_count }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
