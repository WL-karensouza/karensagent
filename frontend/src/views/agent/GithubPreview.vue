<script setup>
import { ref, onMounted, watch } from 'vue'
import { useAgentStore } from '../../stores/agent.js'
import DatePicker from '../../components/DatePicker.vue'
import SelectPicker from '../../components/SelectPicker.vue'

const store = useAgentStore()

const selectedDate = ref('')
const selectedSource = ref('weekly')

onMounted(async () => {
  await store.fetchAvailableDates()
  if (store.availableDates.length > 0) {
    selectedDate.value = store.availableDates[0]
  }
  await loadData()
})

async function loadData() {
  if (!selectedDate.value) return
  await Promise.all([
    store.fetchTrends({ fetch_date: selectedDate.value, source: selectedSource.value }),
    store.fetchNews({ fetch_date: selectedDate.value }),
  ])
}

const sourceOptions = [
  { label: '周榜 (weekly)', value: 'weekly' },
  { label: '月榜 (monthly)', value: 'monthly' },
]

watch(selectedSource, loadData)

/* 日期变化时重新加载数据（跳过初次挂载，已在 onMounted 中触发） */
watch(selectedDate, () => {
  loadData()
})

function formatStars(val) {
  if (!val) return '0'
  return Number(val).toLocaleString()
}
</script>

<template>
  <div>
    <div class="page-header">
      <h1>内容预览</h1>
      <p>按日期查看抓取的 Trend 数据和 AI 资讯</p>
    </div>

    <!-- 日期 & 来源选择 -->
    <div class="card" style="margin-bottom:24px;">
      <div style="display:flex;gap:16px;align-items:flex-end;flex-wrap:wrap;">
        <div class="form-group" style="margin-bottom:0;min-width:220px;">
          <label class="form-label">日期</label>
          <DatePicker v-model="selectedDate" :dates="store.availableDates" />
        </div>
        <div class="form-group" style="margin-bottom:0;min-width:180px;">
          <label class="form-label">数据来源</label>
          <SelectPicker v-model="selectedSource" :options="sourceOptions" />
        </div>
      </div>
    </div>

    <!-- Trend 列表 -->
    <div class="card" style="margin-bottom:24px;">
      <h3 style="margin-bottom:16px;font-size:1rem;">🔥 GitHub {{ selectedSource === 'weekly' ? '周榜' : '月榜' }} ({{ store.trends.length }})</h3>

      <div v-if="store.trends.length === 0" class="empty-state">
        <div class="empty-icon">📭</div>
        <p>该日期暂无数据</p>
      </div>

      <table v-else class="data-table">
        <thead>
          <tr>
            <th>仓库</th>
            <th>语言</th>
            <th>今日 Stars</th>
            <th>总 Stars</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="repo in store.trends" :key="repo.id || repo.repo_name">
            <td>
              <a :href="repo.repo_url" target="_blank" class="repo-name">
                {{ repo.repo_name }}
              </a>
              <div class="repo-desc">{{ repo.description }}</div>
            </td>
            <td>
              <span v-if="repo.language" class="lang-tag">{{ repo.language }}</span>
            </td>
            <td>
              <span class="star-badge">⭐ {{ formatStars(repo.stars_today) }}</span>
            </td>
            <td style="color:var(--text-secondary);">{{ formatStars(repo.total_stars) }} ★</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- AI 资讯 -->
    <div class="card">
      <h3 style="margin-bottom:16px;font-size:1rem;">📚 AI 前沿资讯 ({{ store.news.length }})</h3>

      <div v-if="store.news.length === 0" class="empty-state">
        <div class="empty-icon">📭</div>
        <p>该日期暂无资讯</p>
      </div>

      <table v-else class="data-table">
        <thead>
          <tr>
            <th>标题</th>
            <th>来源</th>
            <th>热度</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in store.news" :key="item.id || item.url">
            <td>
              <a :href="item.url" target="_blank" class="repo-name">
                {{ item.title }}
              </a>
            </td>
            <td>
              <span class="tag" :class="{ active: item.source === 'arxiv' }">
                {{ item.source === 'hackernews' ? '💬 HN' : '📄 ArXiv' }}
              </span>
            </td>
            <td>
              <span v-if="item.score" class="star-badge">{{ item.score }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
