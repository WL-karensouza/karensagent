<!-- 报告元信息：时间 + Token -->
<script setup>
defineProps({
  createdAt: { type: String, default: '' },
  tokenUsed: { type: [Number, String], default: 0 },
})
</script>

<template>
  <div class="meta-foot">
    <span v-if="createdAt">生成时间：{{ createdAt }}</span>
    <span v-if="createdAt && tokenUsed" class="meta-sep">｜</span>
    <span v-if="tokenUsed">Token：{{ tokenUsed }}</span>
  </div>
</template>

<style scoped>
.meta-foot {
  text-align: center;
  font-size: 0.78rem;
  color: var(--text-muted);
  padding: 12px 0;
}
.meta-sep {
  margin: 0 8px;
  opacity: 0.4;
}
</style>
