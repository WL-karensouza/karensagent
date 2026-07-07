<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useStockStore } from '../../stores/stock.js'
import { scoreColor, decisionBadge } from '../../utils/stock.js'

const router = useRouter()
const store = useStockStore()
const page = ref(1)
const pageSize = 10

onMounted(() => {
  store.fetchHistoryReports(page.value, pageSize)
})

function goReport(id) {
  if (!id || id <= 0) return
  router.push(`/agent/stock/report/${id}`)
}

function loadPage(p) {
  page.value = p
  store.fetchHistoryReports(p, pageSize)
}

const totalPages = () => Math.max(1, Math.ceil(store.historyReportsTotal / pageSize))

</script>

<template>
  <div>
    <div class="page-header">
      <h1>历史报告</h1>
      <p>所有已生成的个股分析报告</p>
    </div>

    <div class="card">
      <div v-if="store.loading" class="loading">
        <span class="spinner"></span> 加载中...
      </div>

      <div v-else-if="store.historyReports.length === 0" class="empty-state">
        <p>暂无历史报告</p>
        <button class="btn btn-primary" style="margin-top:16px;" @click="router.push('/agent/stock')">
          去分析第一只股票
        </button>
      </div>

      <template v-else>
        <table class="data-table">
          <thead>
            <tr>
              <th>股票名称</th>
              <th>代码</th>
              <th>评分</th>
              <th>判断</th>
              <th>生成时间</th>
              <th>Token</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in store.historyReports" :key="r.id">
              <td style="font-weight:600;">{{ r.stock_name }}</td>
              <td>{{ r.stock_code }}</td>
              <td>
                <span :style="{color: scoreColor(r.score), fontWeight:700, fontSize:'1.1rem'}">{{ r.score }}</span>
              </td>
              <td><span class="tag active">{{ decisionBadge(r.decision) }}</span></td>
              <td style="color:var(--text-secondary);font-size:0.85rem;">{{ r.created_at?.slice(0, 16) }}</td>
              <td style="color:var(--text-muted);font-size:0.85rem;">{{ r.token_used }}</td>
              <td>
                <button class="btn btn-outline btn-sm" @click="goReport(r.id)">查看</button>
                <button class="btn btn-outline btn-sm" style="margin-left:6px;" @click="store.pushToFeishu(r.id)">📤 推送</button>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- 分页 -->
        <div v-if="store.historyReportsTotal > pageSize" style="display:flex;justify-content:center;align-items:center;gap:8px;margin-top:20px;">
          <button
            class="btn btn-outline btn-sm"
            :disabled="page <= 1"
            @click="loadPage(page - 1)"
          >
            ← 上一页
          </button>
          <span style="font-size:0.9rem;color:var(--text-secondary);">
            {{ page }} / {{ totalPages() }}（共 {{ store.historyReportsTotal }} 条）
          </span>
          <button
            class="btn btn-outline btn-sm"
            :disabled="page >= totalPages()"
            @click="loadPage(page + 1)"
          >
            下一页 →
          </button>
        </div>
      </template>
    </div>
  </div>
</template>
