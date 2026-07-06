<script setup>
import { onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useStockStore } from '../../stores/stock.js'

const route = useRoute()
const router = useRouter()
const store = useStockStore()
const reportId = computed(() => route.params.id)

onMounted(() => {
  const id = Number(reportId.value)
  if (!id || id <= 0) {
    store.showToast('无效的报告 ID')
    router.replace('/agent/stock')
    return
  }
  store.fetchReportDetail(id)
})

/* 评分颜色 */
function scoreColor(score) {
  if (score >= 70) return 'var(--green)'
  if (score >= 40) return 'var(--accent)'
  return 'var(--red)'
}

function decisionBadge(d) {
  if (!d) return ''
  if (d.includes('看多')) return '🟢 ' + d
  if (d.includes('看空')) return '🔴 ' + d
  return '🟡 ' + d
}

/* 解析 report_json 为结构化数据 */
const reportData = computed(() => {
  const row = store.currentReport
  if (!row) return null
  try {
    if (typeof row.report_json === 'string') {
      return JSON.parse(row.report_json)
    }
    return row.report_json
  } catch {
    return null
  }
})

/* Markdown 渲染为 HTML（简易版） */
const mdHtml = computed(() => {
  const row = store.currentReport
  if (!row || !row.markdown) return ''
  let md = row.markdown
  // 转义 HTML
  md = md.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  // 标题
  md = md.replace(/^### (.+)$/gm, '<h4>$1</h4>')
  md = md.replace(/^## (.+)$/gm, '<h3>$1</h3>')
  md = md.replace(/^# (.+)$/gm, '<h2>$1</h2>')
  // 粗体
  md = md.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  // 行内代码
  md = md.replace(/`([^`]+)`/g, '<code>$1</code>')
  // 引用
  md = md.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>')
  // 列表
  md = md.replace(/^- (.+)$/gm, '<li>$1</li>')
  // 分隔线
  md = md.replace(/^---$/gm, '<hr>')
  // 段落（连续两个换行）
  md = md.replace(/\n\n/g, '</p><p>')
  // 单换行
  md = md.replace(/\n/g, '<br>')
  return '<p>' + md + '</p>'
})

async function handlePush() {
  const row = store.currentReport
  if (!row) return
  await store.pushToFeishu(row.id)
}
</script>

<template>
  <div>
    <div class="page-header">
      <button class="btn btn-outline btn-sm" @click="router.push('/agent/stock')" style="margin-bottom:12px;">
        ← 返回仪表盘
      </button>
      <h1 v-if="store.currentReport">
        {{ store.currentReport.stock_name }}（{{ store.currentReport.stock_code }}）分析报告
      </h1>
    </div>

    <!-- 加载中 -->
    <div v-if="!store.currentReport" class="card">
      <div class="loading">
        <span class="spinner"></span> 加载报告...
      </div>
    </div>

    <template v-else>
      <!-- 评分概览 -->
      <div class="card" style="margin-bottom:24px;">
        <div style="display:flex;align-items:center;gap:20px;flex-wrap:wrap;">
          <div style="text-align:center;">
            <div style="font-size:3rem;font-weight:700;" :style="{color: scoreColor(store.currentReport.score)}">
              {{ store.currentReport.score }}
            </div>
            <div style="font-size:0.85rem;color:var(--text-secondary);">综合评分</div>
          </div>
          <div>
            <span class="tag active" style="font-size:1rem;">{{ decisionBadge(store.currentReport.decision) }}</span>
          </div>
          <div style="flex:1;min-width:200px;">
            <!-- 评分进度条 -->
            <div class="bar-track" style="height:12px;">
              <div
                class="bar-fill"
                :style="{width: store.currentReport.score + '%', background: scoreColor(store.currentReport.score)}"
              ></div>
            </div>
          </div>
          <div style="display:flex;gap:8px;">
            <button class="btn btn-outline btn-sm" @click="handlePush">📤 推送到飞书</button>
          </div>
        </div>
        <p v-if="reportData && reportData.summary" style="margin-top:12px;color:var(--text-secondary);font-size:0.9rem;">
          {{ reportData.summary }}
        </p>
      </div>

      <!-- Markdown 报告内容 -->
      <div class="card">
        <div class="markdown-body" v-html="mdHtml"></div>
      </div>

      <!-- 元信息 -->
      <div style="margin-top:16px;color:var(--text-muted);font-size:0.8rem;text-align:center;">
        生成时间：{{ store.currentReport.created_at }} ｜ Token：{{ store.currentReport.token_used }}
      </div>
    </template>
  </div>
</template>

<style scoped>
/* Markdown 内容样式 */
.markdown-body h2 { font-size:1.3rem; margin:24px 0 12px; color:var(--text-primary); }
.markdown-body h3 { font-size:1.1rem; margin:20px 0 10px; color:var(--text-primary); }
.markdown-body h4 { font-size:1rem; margin:16px 0 8px; color:var(--text-primary); }
.markdown-body p { margin:8px 0; line-height:1.8; color:var(--text-secondary); }
.markdown-body blockquote {
  margin:12px 0;
  padding:12px 16px;
  background:var(--bg-subtle);
  border-left:3px solid var(--accent);
  border-radius:0 var(--radius-sm) var(--radius-sm) 0;
  color:var(--text-secondary);
}
.markdown-body li { margin:4px 0 4px 20px; color:var(--text-secondary); }
.markdown-body code {
  background:var(--bg-hover);
  padding:2px 6px;
  border-radius:4px;
  font-size:0.85em;
  color:var(--accent);
}
.markdown-body hr { border:none; border-top:1px solid var(--border-light); margin:24px 0; }
.markdown-body strong { color:var(--text-primary); }
</style>
