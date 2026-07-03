<script setup>
import { ref, onMounted } from 'vue'
import { useAgentStore } from '../../stores/agent.js'

const store = useAgentStore()

/* ── 关键词表单 ── */
const newKeyword = ref('')

/* ── 飞书 Webhook ── */
const feishuUrl = ref('')

onMounted(async () => {
  await Promise.all([
    store.fetchKeywords(),
    store.fetchWebhook(),
  ])
})

async function handleAddKeyword() {
  if (!newKeyword.value.trim()) {
    store.showToast('请输入关键词')
    return
  }
  const res = await store.addKeyword({ keyword: newKeyword.value.trim(), score: 0, enabled: 1 })
  if (res.code === 0) {
    newKeyword.value = ''
  }
}

async function handleToggleKeyword(kw) {
  await store.updateKeyword(kw.keyword, { enabled: kw.enabled ? 0 : 1 })
}

async function handleDeleteKeyword(kw) {
  await store.deleteKeyword(kw.keyword)
}

async function handleSaveWebhook() {
  if (!feishuUrl.value.trim()) {
    store.showToast('请输入飞书 Webhook URL')
    return
  }
  await store.updateWebhook(feishuUrl.value.trim())
}
</script>

<template>
  <div>
    <div class="page-header">
      <h1>配置管理</h1>
      <p>管理关键词过滤规则和飞书推送渠道</p>
    </div>

    <!-- ── 关键词管理 ── -->
    <div class="card" style="margin-bottom:24px;">
      <h3 style="margin-bottom:16px;font-size:1rem;">🏷️ 关键词过滤</h3>
      <p style="font-size:0.85rem;color:var(--text-secondary);margin-bottom:16px;">
AI 资讯标题或摘要命中关键词则会被推送到飞书。仓库榜单已改为纯 Stars 排名，不再使用关键词过滤。
      </p>

      <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px;">
        <span
          v-for="kw in store.keywords"
          :key="kw.keyword"
          :class="['tag', kw.enabled ? 'active' : '']"
          style="cursor:pointer;"
          @click="handleToggleKeyword(kw)"
          :title="kw.enabled ? '点击禁用' : '点击启用'"
        >
          {{ kw.keyword }}
          <span class="tag-remove" @click.stop="handleDeleteKeyword(kw)">×</span>
        </span>
      </div>

      <div style="display:flex;gap:12px;align-items:flex-end;flex-wrap:wrap;">
        <div class="form-group" style="margin-bottom:0;min-width:200px;">
          <label class="form-label">新关键词</label>
          <input
            v-model="newKeyword"
            class="form-input"
            placeholder="e.g. langgraph"
            @keyup.enter="handleAddKeyword"
          />
        </div>
        <button class="btn btn-primary btn-sm" @click="handleAddKeyword">+ 添加</button>
      </div>
    </div>

    <!-- ── 飞书 Webhook ── -->
    <div class="card" style="margin-bottom:24px;">
      <h3 style="margin-bottom:16px;font-size:1rem;">📋 飞书推送</h3>

      <div class="form-group">
        <label class="form-label">
          飞书机器人 Webhook
          <span v-if="store.webhooks.configured" class="tag active" style="margin-left:8px;font-size:0.7rem;">已配置</span>
        </label>
        <div style="display:flex;gap:8px;">
          <input
            v-model="feishuUrl"
            class="form-input"
            placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/..."
          />
          <button class="btn btn-outline btn-sm" @click="handleSaveWebhook">保存</button>
        </div>
      </div>
    </div>

    <!-- ── 推送时间 ── -->
    <div class="card">
      <h3 style="margin-bottom:16px;font-size:1rem;">⏰ 推送时间</h3>
      <p style="font-size:0.9rem;color:var(--text-secondary);">
        当前设置：每天早上 <strong>09:00</strong> 自动推送到飞书。
      </p>
      <p style="font-size:0.8rem;color:var(--text-muted);margin-top:8px;">
        修改推送时间请编辑服务器上的 <code>.env</code> 文件中的 <code>PUSH_TIME</code> 变量。
      </p>
    </div>
  </div>
</template>
