<!-- PROTOTYPE — AI 问答助理占位面板（三变体共用，设计已锁定；未来直接升级为会话容器） -->
<script setup>
/* 占位期内容：助理标识 + 即将上线徽章 + 说明 + 示例问题 + 禁用输入框 */
</script>

<template>
  <aside class="ai-panel">
    <!-- 头部：标识 + 徽章 -->
    <header class="ai-head">
      <div class="ai-id">
        <!-- 线性对话图标 -->
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
        </svg>
        <strong>AI 问答助理</strong>
      </div>
      <span class="ai-badge">即将上线</span>
    </header>

    <!-- 会话区：占位态展示说明 + 呼吸点 + 示例问题；上线后此处滚动承载消息 -->
    <div class="ai-body">
      <!-- 说明 -->
      <p class="ai-desc">对报告内容追问、解读数据、厘清结论逻辑。</p>

      <!-- 呼吸三点：唯一的"活"元素，暗示 AI 正在路上 -->
      <div class="ai-dots" aria-hidden="true"><i></i><i></i><i></i></div>

      <!-- 示例问题：从报告语境中来，建立使用预期 -->
      <div class="ai-examples">
        <p class="ai-ex-title">你可以这样问：</p>
        <ul>
          <li>估值判断的依据是什么？</li>
          <li>主要风险点有哪些？</li>
          <li>北向资金动向稳定吗？</li>
        </ul>
      </div>
    </div>

    <!-- 输入区（原底部 followup-box 移入，禁用占位；钉在面板底部） -->
    <footer class="ai-input">
      <input type="text" disabled placeholder="即将上线，敬请期待" />
      <button type="button" disabled>发送</button>
    </footer>
  </aside>
</template>

<style scoped>
/* AI 助理面板：中性卡片，hover 边框微深 + 轻阴影 */
/* 满高聊天面板：顶栏 + 会话区(可滚动) + 钉底输入，外形不随内容跳动 */
.ai-panel {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: calc(100vh - var(--topnav-height, 64px) - 48px);
  min-height: 520px;
  box-sizing: border-box;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
/* 会话区占满中间，内容溢出时内部滚动 */
.ai-body {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.ai-panel:hover {
  border-color: var(--sent-soft);
  box-shadow: 0 4px 16px rgba(45, 42, 38, 0.06);
}
.ai-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.ai-id {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--sent-strong);
  font-size: 0.92rem;
}
.ai-badge {
  font-size: 0.7rem;
  padding: 3px 10px;
  border-radius: 999px;
  background: var(--sent-bg);
  color: var(--sent-mid);
  border: 1px solid var(--border-color);
}
.ai-desc {
  margin: 0;
  font-size: 0.8rem;
  color: var(--sent-mid);
  line-height: 1.6;
}
/* 呼吸三点：灰阶、缓慢、错峰 */
.ai-dots {
  display: flex;
  gap: 6px;
}
.ai-dots i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--sent-soft);
  animation: ai-breathe 1.8s ease-in-out infinite;
}
.ai-dots i:nth-child(2) { animation-delay: 0.3s; }
.ai-dots i:nth-child(3) { animation-delay: 0.6s; }
@keyframes ai-breathe {
  0%, 100% { opacity: 0.3; transform: scale(0.85); }
  50% { opacity: 1; transform: scale(1); }
}
.ai-examples {
  background: var(--sent-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 12px 14px;
}
.ai-ex-title {
  margin: 0 0 6px;
  font-size: 0.74rem;
  color: var(--sent-mid);
}
.ai-examples ul {
  margin: 0;
  padding-left: 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.ai-examples li {
  font-size: 0.78rem;
  color: var(--sent-strong);
  line-height: 1.5;
}
.ai-input {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
  padding-top: 14px;
  border-top: 1px solid var(--border-color);
}
.ai-input input {
  flex: 1;
  min-width: 0;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 9px 12px;
  font-size: 0.8rem;
  font-family: inherit;
  color: var(--sent-mid);
  background: var(--bg-subtle);
  outline: none;
  cursor: not-allowed;
}
.ai-input button {
  height: 36px;
  padding: 0 16px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  font-size: 0.78rem;
  font-family: inherit;
  color: var(--sent-mid);
  cursor: not-allowed;
  opacity: 0.6;
}
</style>
