<script setup>
/* ═══════════════════════════════════════════
   OfficeScene —— 3D 场景组合根组件
   组合房间 / 装饰 / 两个工位 / 大屏 / 名牌
   会谈调度：随机触发两人走向中央对话 → 3 轮后回工位坐下
   事件向上抛给 OfficeHome，本组件不直接操作路由
   ═══════════════════════════════════════════ */
import { ref, onMounted, onUnmounted } from 'vue'
import { TresCanvas } from '@tresjs/core'
import { OrbitControls } from '@tresjs/cientos'
import OfficeRoom from './OfficeRoom.vue'
import OfficeDesk from './OfficeDesk.vue'
import OfficeWorker from './OfficeWorker.vue'
import OfficeNameplate from './OfficeNameplate.vue'
import OfficeWallScreen from './OfficeWallScreen.vue'
import OfficeDecorations from './OfficeDecorations.vue'
import OfficeCameraClamp from './OfficeCameraClamp.vue'
import CharacterBubble from '../../three/character/CharacterBubble.vue'

/* 事件向上抛：go-agent（跳转）/ ready（场景就绪） */
const emit = defineEmits(['go-agent', 'ready'])

/* 对话气泡层引用（组件实例的 show(text, position)） */
const bubbleRef = ref(null)

/* 两个工人的组件实例（模板 ref 收集，供会谈调度 walkTo 驱动） */
const ai_news = ref(null)
const stock = ref(null)
const workers = { ai_news, stock }

/* 台词库（随机轮换） */
const LINES = [
  '今天的大盘数据有点意思，你看看？',
  '我刚跑了最新的策略回测，收益不错！',
  '这个新闻热点值得追踪，帮我盯着点。',
  '午后那波行情你看到了吗？',
  '我整理了一份周报，晚点发你。',
]

/* 会谈调度：启动后随机触发两人走向中央 → 轮流气泡对话
   3 轮结束后各自走回工位并坐下，再随机定时触发下一轮 */
let talkTimer = null
let talkInterval = null
function startMeeting() {
  talkTimer = setTimeout(() => {
    // 两人走向中央会谈区（直接调用组件实例 walkTo 驱动，不再走事件分发自环）
    onWorkerGo('ai_news', 0, -0.5)
    onWorkerGo('stock', 1.2, -0.5)
    // 轮流冒泡：气泡跟随说话者（头顶上方 y≈2.0）
    const lines = shuffle(LINES)
    const SPEAK_POS = {
      ai_news: { x: 0, y: 2, z: -0.5 },
      stock: { x: 1.2, y: 2, z: -0.5 },
    }
    let i = 0
    talkInterval = setInterval(() => {
      const line = lines[i % lines.length]
      const speaker = i % 2 === 0 ? 'ai_news' : 'stock'
      bubbleRef.value?.show(line, SPEAK_POS[speaker])
      i++
      if (i >= 3) {
        clearInterval(talkInterval)
        talkInterval = null
        finishMeeting()
        scheduleNext()
      }
    }, 2000)
  }, 4000)
}

/* 会谈结束：两人各自走回工位，到达后坐下（sit 落座 + sitIdle 打字） */
function finishMeeting() {
  walkHome('ai_news', -3, -2)
  walkHome('stock', 3, -2)
}
/* 走向工位 → 到达回调里坐下（walkTo 的 onArrive 单次触发） */
function walkHome(id, x, z) {
  const el = workers[id]?.value
  el?.walkTo(x, z, () => el.sitDown())
}

function scheduleNext() {
  talkTimer = setTimeout(startMeeting, 20000 + Math.random() * 15000)
}

/* 台词库随机轮换：Fisher-Yates 打乱，保证每轮台词顺序真正随机 */
function shuffle(arr) {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

function onSceneReady() {
  emit('ready')
}
/* 工人点击 → 上抛 go-agent，路由跳转交给 OfficeHome */
function onWorkerClick(agentId) {
  emit('go-agent', agentId)
}

/* 通过组件实例驱动对应工人走向目标（Task 6 walkTo，世界坐标）
   由本组件的会谈调度直接调用，无外部事件自环 */
function onWorkerGo(id, x, z) {
  workers[id]?.value?.walkTo(x, z)
}

onMounted(() => {
  startMeeting()
})
onUnmounted(() => {
  clearTimeout(talkTimer)
  if (talkInterval) clearInterval(talkInterval)
})
</script>

<template>
  <TresCanvas
    shadows
    antialias
    clear-color="#ECE8E0"
    @ready="onSceneReady"
  >
    <!-- 主相机：墙内较高俯视；fov 放宽 + 视线上抬，确保后墙大屏顶部完整入镜（初值肉眼可调） -->
    <TresPerspectiveCamera :position="[0, 4.3, 4.3]" :fov="60" />
    <!-- 轨道控制：左键旋转 / 滚轮缩放；禁用平移防视角歪出房间；不限制 azimuth = 横向 360° -->
    <!-- 距离/角度不做球形限制，统一由 OfficeCameraClamp 夹盒（注：zoom 到边界的抖动属问题2，待架构决策） -->
    <OrbitControls
      :enableDamping="true"
      :enablePan="false"
      :minDistance="2"
      :target="[0, 1.1, -1.6]"
    />

    <OfficeRoom />
    <OfficeDecorations />

    <!-- AI 前沿工位（左侧） → /agent/ai_news -->
    <OfficeDesk :position="[-3, 0, -2]" theme="ai_news" />
    <OfficeWorker ref="ai_news" worker-id="ai_news" :position="[-3, 0, -2]" @select="onWorkerClick" />
    <OfficeNameplate :position="[-3, 0.02, -0.6]" text="AI 前沿" />

    <!-- 股票分析工位（右侧） → /agent/stock -->
    <OfficeDesk :position="[3, 0, -2]" theme="stock" />
    <OfficeWorker ref="stock" worker-id="stock" :position="[3, 0, -2]" @select="onWorkerClick" />
    <OfficeNameplate :position="[3, 0.02, -0.6]" text="股票分析" />

    <!-- 墙面大屏（静态占位） -->
    <OfficeWallScreen :position="[0, 2.2, -4.8]" />

    <!-- 相机夹盒：每帧把相机位置限制在房间包围盒内，保证视角永不离房间（须排在 OrbitControls 之后注册） -->
    <OfficeCameraClamp />

    <!-- 对话气泡层（世界坐标投影） -->
    <CharacterBubble ref="bubbleRef" />
  </TresCanvas>
</template>

<style scoped>
/* TresCanvas 会填满父容器；父级尺寸由 OfficeHome（Phase 5）提供 */
</style>
