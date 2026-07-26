<script setup>
import { onMounted } from 'vue'
import { useAgentStore } from '../../stores/agent.js'

const store = useAgentStore()

onMounted(() => {
  store.fetchHistory()
})
</script>

<template>
  <div>
    <div class="page-header">
      <h1>推送历史</h1>
      <p>AI 新闻推送记录</p>
    </div>

    <div class="card" v-if="store.pushHistory.length === 0">
      <div class="empty-state">
        <p style="font-weight:600;color:var(--text-primary);">暂无推送记录</p>
        <p style="margin-top:4px;color:var(--text-muted);">等待定时任务或手动触发首次推送</p>
      </div>
    </div>

    <div class="card" v-else>
      <table class="data-table">
        <thead>
          <tr>
            <th>推送时间</th>
            <th>平台</th>
            <th>资讯数</th>
            <th>状态</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in store.pushHistory" :key="item.id">
            <td>{{ item.push_time }}</td>
            <td>{{ item.platform === 'feishu' ? '飞书' : item.platform }}</td>
            <td>{{ item.news_count }}</td>
            <td>
              <span :class="['tag', item.status === 'sent' ? 'active' : '']">
                {{ item.status === 'sent' ? '已发送' : '失败' }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
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
.tag {
  font-size: 0.78rem;
  padding: 2px 10px;
  border-radius: 999px;
  background: var(--bg-hover);
  color: var(--text-muted);
}
.tag.active {
  background: var(--green-light, #dcfce7);
  color: var(--green, #16a34a);
}
.empty-state {
  text-align: center;
  padding: 40px 0;
}
</style>
