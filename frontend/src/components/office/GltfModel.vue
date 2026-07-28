<script setup>
/* ═══════════════════════════════════════════
   GltfModel —— 通用 glTF 模型包装组件（同步组件，无需 Suspense）
   用法（可嵌在 TresCanvas 场景图任意位置）：
     <GltfModel src="/models/decor/plant.glb" :size="1.3" :position="[-6, 0, -4]">
       <template #fallback>…原几何体兜底…</template>
     </GltfModel>
   设计要点：
   1. 加载逻辑全在 useModel composable（响应式 watch，非 await）→ 组件只负责模板
   2. 加载失败（404 / 损坏）loadError 置位 → 渲染 fallback 插槽 → 场景永不白屏
   3. 缩放/居中/落地由 normalizeModel 自动处理，业务侧只声明"要多大、放哪里"
   4. position / rotation 作用于外层分组，模型归一化在内层互不干扰
   ═══════════════════════════════════════════ */
import { useModel } from '../../composables/useModel'

const props = defineProps({
  /* 模型路径，如 '/models/furniture/desk_workstation.glb' */
  src: { type: String, required: true },
  /* 目标尺寸：数字=按最长边适配（米）；[w,h,d]=各轴独立适配；null=保持原始尺寸 */
  size: { type: [Number, Array], default: null },
  /* 外层分组在场景中的位置 [x, y, z] */
  position: { type: Array, default: () => [0, 0, 0] },
  /* 外层分组旋转 [x, y, z]（弧度） */
  rotation: { type: Array, default: () => [0, 0, 0] },
  /* 加载并归一化后、挂载前的场景级微调钩子，签名 (scene) => void（如拆开椅子节点） */
  prepare: { type: Function, default: null },
})

/* 响应式加载：modelScene 就绪即渲染，loadError 即降级 */
const { modelScene, loadError } = useModel(props.src, { size: props.size, prepare: props.prepare })
</script>

<template>
  <TresGroup :position="position" :rotation="rotation">
    <!-- 加载成功 → 渲染 glTF 根节点 -->
    <primitive v-if="modelScene" :object="modelScene" />
    <!-- 加载失败 → 渲染 fallback 插槽（调用方传入的原几何体组合） -->
    <slot v-else-if="loadError" name="fallback" />
  </TresGroup>
</template>
