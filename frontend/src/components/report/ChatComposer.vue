<!-- 问答输入容器：浅灰托盘内嵌白色输入框，含底部工具行与点阵发送键（astryx landing 形态） -->
<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import matrixIdle from '../../assets/chat/matrix-idle.svg'
import matrixRun from '../../assets/chat/matrix-loader.svg'

const props = defineProps({
  modelValue: { type: String, default: '' },
  /* landing = 收拢态舒展档；compact = 展开态紧凑档 */
  density: { type: String, default: 'landing' },
  maxRows: { type: Number, default: 5 },
  disabled: { type: Boolean, default: false },
  /* AI 思考中：发送键切为点阵动画并禁止再次发送（不承担中止）；
     只影响发送闸门，不锁输入框——要连输入一起锁就额外传 disabled */
  loading: { type: Boolean, default: false },
  placeholder: { type: String, default: '输入问题，Enter 发送' },
})

const emit = defineEmits(['update:modelValue', 'send'])

/* 行高与 textarea 高度计算保持一致（见样式里 line-height: 22px） */
const LINE_HEIGHT = 22

const text = ref(props.modelValue)
const taRef = ref(null)

/* 外部改值（如发送后清空、切换股票重置）同步进内部状态 */
watch(() => props.modelValue, (v) => { text.value = v })

/* 空输入、外部禁用、AI 思考中，三者都不可发送 */
const canSend = computed(
  () => !props.disabled && !props.loading && text.value.trim().length > 0,
)

function syncHeight() {
  const ta = taRef.value
  if (!ta) return
  ta.style.height = 'auto'
  const max = props.maxRows * LINE_HEIGHT
  ta.style.height = Math.min(ta.scrollHeight, max) + 'px'
}

function onInput(e) {
  text.value = e.target.value
  emit('update:modelValue', text.value)
  syncHeight()
}

function doSend() {
  if (!canSend.value) return
  emit('send')
  text.value = ''
  emit('update:modelValue', '')
  /* 发送后高度复位到单行/最小高度 */
  nextTick(() => {
    const ta = taRef.value
    if (ta) ta.style.height = ''
  })
}

/* Enter 发送 / Shift+Enter 换行；中文输入法选词回车（isComposing / 229）必须放行 */
function onKeydown(e) {
  if (e.key !== 'Enter') return
  if (e.shiftKey) return
  if (e.isComposing || e.keyCode === 229) return
  e.preventDefault()
  doSend()
}

defineExpose({ focus: () => taRef.value?.focus() })
</script>

<template>
  <div class="composer-tray" :class="`is-${density}`">
    <div class="composer-inner">
      <textarea
        ref="taRef"
        class="composer-textarea"
        :value="text"
        :placeholder="placeholder"
        :disabled="disabled"
        rows="1"
        @input="onInput"
        @keydown="onKeydown"
      ></textarea>
      <div class="composer-tools">
        <!-- 静/动两态叠在同一格里：空闲显示静止白点阵，思考中播放动画 -->
        <button
          class="composer-send"
          :class="{ 'is-thinking': loading }"
          type="button"
          :disabled="!canSend"
          :aria-label="loading ? 'AI 正在思考' : '发送'"
          :aria-busy="loading ? 'true' : undefined"
          @click="doSend"
        >
          <img
            class="composer-matrix composer-matrix--idle"
            :src="matrixIdle"
            alt=""
            aria-hidden="true"
          />
          <img
            class="composer-matrix composer-matrix--run"
            :src="matrixRun"
            alt=""
            aria-hidden="true"
          />
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 外层托盘：浅灰底 + 大圆角 + 悬浮阴影，聚焦时阴影加深 */
.composer-tray {
  background: var(--ax-hover);
  border-radius: var(--ax-radius-tray);
  padding: var(--ax-pad-tray);
  box-shadow: var(--ax-shadow-low);
  transition: box-shadow 0.15s ease;
}
.composer-tray:focus-within { box-shadow: var(--ax-shadow-med); }
.composer-tray.is-compact { padding: var(--ax-pad-tray-compact); }

/* 内层白框：承载输入与工具行 */
.composer-inner {
  background: var(--ax-surface);
  border-radius: var(--ax-radius-inner);
  padding: 9px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.composer-tray.is-compact .composer-inner { padding: 6px 10px; gap: 4px; }

/* 输入区：无边框无轮廓，高度由脚本按内容与 maxRows 计算 */
.composer-textarea {
  border: none;
  outline: none;
  resize: none;
  background: transparent;
  font-family: inherit;
  font-size: 0.82rem;
  line-height: 22px;
  color: var(--ax-text);
  overflow-y: auto;
  padding: 0;
  display: block;
  width: 100%;
  box-sizing: border-box;
}
.composer-textarea::placeholder { color: var(--ax-text-secondary); }
.composer-tray.is-landing .composer-textarea { min-height: 63px; }
.composer-tray.is-compact .composer-textarea { min-height: 22px; }

/* 底行：仅保留圆形发送键，右对齐 */
.composer-tools { display: flex; align-items: center; justify-content: flex-end; }
/* 发送键：36px 黑底圆形，内嵌 5×5 点阵（布局照搬 open-design，点色改为白色） */
.composer-send {
  /* 发送键底色：项目 astryx token 里没有近黑档位，收敛为组件内变量，
     避免底色与 hover 混色各写一遍字面量 */
  --send-bg: #202020;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  padding: 0;
  background: var(--send-bg);
  cursor: pointer;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  transition:
    background-color 0.15s ease,
    transform 0.15s ease;
}
.composer-send:hover:not(:disabled) { background: color-mix(in srgb, var(--send-bg) 88%, #fff); }
.composer-send:active:not(:disabled) { transform: translateY(1px); }
.composer-send:focus-visible { outline: 2px solid var(--ax-accent); outline-offset: 2px; }
/* 不可点（空输入 / 思考中 / 外部禁用）时不降透明度，只改光标 */
.composer-send:disabled { cursor: default; }

/* 点阵：两态共占同一网格单元，靠 visibility 切换，互不挤占布局。
   width/height 同时写死，避免 <img> 未加载时按原始尺寸 92px 撑爆按钮。
   两张图都常驻是有意为之（open-design 原版同样常驻）：
   换成 v-if 会在首次进入思考态时露出加载空档，代价大于隐藏 SVG 的微小动画开销 */
.composer-matrix {
  grid-area: 1 / 1;
  width: 20px;
  height: 20px;
  display: block;
  pointer-events: none;
}
.composer-send.is-thinking .composer-matrix--idle { visibility: hidden; }
.composer-send:not(.is-thinking) .composer-matrix--run { visibility: hidden; }
</style>
