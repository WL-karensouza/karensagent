<script setup>
defineProps({
  vertical: { type: Boolean, default: false },
})
</script>

<template>
  <hr v-if="!vertical" class="divider-h" />
  <span v-else class="divider-v" />
</template>

<style scoped>
/* 水平细线 */
.divider-h {
  border: none;
  border-top: 1px solid #e5e7eb;
  margin: 0;
}

/* 垂直细线 */
.divider-v {
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 1px;
  background: #e5e7eb;
}
</style>
