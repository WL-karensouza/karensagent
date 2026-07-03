<script setup>
/* 平台级全局设置页 */
</script>

<template>
  <div>
    <div class="page-header">
      <h1>平台设置</h1>
      <p>管理 Karens Agent 平台的全局配置</p>
    </div>

    <div class="card">
      <div class="empty-state">
        <div class="empty-icon">
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="color:var(--accent);opacity:0.5;">
            <circle cx="12" cy="12" r="3"/>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
          </svg>
        </div>
        <p style="font-weight:600;color:var(--text-primary);">Agent 各自独立配置</p>
        <p style="margin-top:6px;">
          每个 Agent 拥有独立的关键词、Webhook 等配置项。<br/>
          请进入对应 Agent 页面进行详细设置。
        </p>
      </div>
    </div>

    <div style="margin-top:24px;" class="card">
      <h3 style="font-size:0.95rem;font-weight:600;margin-bottom:12px;">Agent 配置入口</h3>
      <div style="display:flex;gap:12px;">
        <router-link to="/agent/github/settings" class="btn btn-outline btn-sm">GitHub 热榜设置</router-link>
        <router-link to="/agent/stock" class="btn btn-outline btn-sm">股票分析（开发中）</router-link>
      </div>
    </div>
  </div>
</template>
