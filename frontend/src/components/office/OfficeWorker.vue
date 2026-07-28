<script setup>
/* ═══════════════════════════════════════════
   OfficeWorker —— 工作人员（双轨：glTF 坐姿真人 + 几何体兜底 + 交互）
   优先 useFBX 加载 Mixamo 坐姿模型（浏览器直接吃 .fbx，零转换），
   useAnimations 播放其坐动画；加载/解析失败或加载中都降级为原几何体人，永不闪空白
   交互保留：悬浮放大 1.05× + pointer 光标 + 点击上抛 select（路由跳转交给上层）
   主题色（橙/蓝）仅作用于兜底几何体衬衫；glTF 模型衣色固定，主题靠工位屏幕/名牌体现
   坐姿对齐（运行时实测椅子，不猜任何坐标/绝对尺寸）：
     - 测椅子：遍历含 'Chair' 的节点后**去重为椅子根**（零件名也含 Chair，不去重会拆成 N 块量脏数据）
     - 尺度：onRender 实测整椅椅背顶，人头目标 = 椅背顶 × 比例（单一杠杆同时控头视觉+屁股座面）
     - 垂直：缩放后脚踩地；比例取对时屁股因坐姿固有比例自然≈座面，无需单独猜座面 y
     - 水平：把屁股骨骼 Hips 的水平位置钉到最近椅子上
   胳膊抬升：useAnimations 的 onBeforeRender 先 update 动画 pose，本组件后注册的 onBeforeRender
     再覆盖左右 Arm 骨骼的 x 旋转，把手从悬空抬向桌面（ARM_RAISE 初始估值，面板测手高后精调）
   诊断面板（调试脚手架，验收后整段删）：左上角 fixed 黄底 div，覆盖成功+所有早退分支，
     截图即得椅子实测尺寸/手高/卡点，免去开 devtools/抄 console（详见 setDiag / onUnmounted）
   交付链路探针 BUILD_TAG：每次改动递增，setup 一执行就写进面板（验收后删）
   ═══════════════════════════════════════════ */
import { ref, shallowRef, computed, watch, nextTick, onUnmounted } from 'vue'
import { useFBX, useAnimations } from '@tresjs/cientos'
import { useLoop, useTres } from '@tresjs/core'
import { Box3, Vector3 } from 'three'
/* 归一化（居中/落地/阴影）复用桌子的工具，保持场景一致 */
import { normalizeModel } from '../../composables/useModel'

const props = defineProps({
  /* 工位位置 [x, y, z]（与对应办公桌一致） */
  position: { type: Array, default: () => [0, 0, 0] },
  /* Agent id：ai_news | stock */
  workerId: { type: String, default: 'ai_news' },
})

/* 点击上抛给 OfficeScene，本组件不碰 router */
const emit = defineEmits(['select'])

/* 衬衫主题色：仅兜底几何体使用（AI 前沿橙 / 股票分析深蓝） */
const shirt = computed(() => (props.workerId === 'stock' ? '#1E3A8A' : '#D97706'))
const SKIN = '#F0C8A8'
const PANTS = '#3A3E45'

/* 模型路径：文件名含空格，URL 用 %20 编码避免 404（不改动磁盘上的原文件） */
const FBX_PATH = '/models/worker/Seated%20Idle.fbx'

/* 朝桌旋转：截图初看朝向正确，保留；若歪按 90° 步进调 */
const SEAT_ROT_Y = Math.PI
/* 临时兜底坐高（米）：仅椅子未加载那一两帧的显示尺寸；最终由 onRender 纠正 */
const TARGET_SEAT_H = 1.8
/* 人头目标 = 整椅椅背顶 × 此比例。1.5 探针已确认通路但偏巨人，按"适当调小"回到 1.3（饱满不冒顶） */
const SEAT_HEAD_RATIO = 1.3
/* 胳膊抬升（弧度）：覆盖动画让手从悬空抬向桌面。初始估值，方向/大小据面板 leftHandY vs deskY 精调；
   手还低于桌面→加大或翻号，手高过桌面→减小 */
const ARM_RAISE = 0.4

/* 交付链路探针版本号：改代码就递增；面板出现它=最新代码已进浏览器 */
const BUILD_TAG = 'v6'

/* ── 诊断面板（脚手架，验收后删）：只让 ai_news 实例挂一个 div，两工人椅子同模型看一个即可 ── */
const diag = ref('init')
let diagEl = null
if (typeof document !== 'undefined' && props.workerId === 'ai_news') {
  diagEl = document.createElement('div')
  diagEl.setAttribute('data-worker-diag', '')
  diagEl.style.cssText =
    'position:fixed;left:8px;top:8px;z-index:99999;padding:6px 10px;' +
    'background:#FFE600;color:#000;font:12px/1.5 monospace;border-radius:6px;' +
    'box-shadow:0 2px 8px rgba(0,0,0,.3);max-width:480px;white-space:pre-wrap;pointer-events:none'
  document.body.appendChild(diagEl)
}
/* 值不变不写 DOM，避免每帧刷；所有串带 BUILD_TAG 前缀 */
const setDiag = (s) => {
  const full = `${BUILD_TAG} ${s}`
  if (full === diag.value) return
  diag.value = full
  if (diagEl) diagEl.textContent = `[worker] ${full}`
}
/* setup 同步执行即写一次：专测交付链路 */
setDiag('init (setup ran)')
onUnmounted(() => {
  if (diagEl && diagEl.parentNode) diagEl.parentNode.removeChild(diagEl)
})

/* 按关键字模糊匹配骨骼/节点（此 Mixamo 骨架根为 mixamorigHips） */
function findBone(root, keyword) {
  let hit = null
  root.traverse((n) => {
    if (!hit && n.name && n.name.includes(keyword)) hit = n
  })
  return hit
}

/* 加载 glTF：state 异步就绪；error 触发兜底 */
const { state, error } = useFBX(FBX_PATH)
/* three 对象禁深代理（modelViewMatrix 崩溃防护），与 useModel 同模式 */
const modelScene = shallowRef(null)
const anims = shallowRef([])
const loadError = ref(false)

/* 待对齐的模型根：归一化+临时缩放+落地已完成，差"尺度按椅子纠正 + 屁股→椅子水平对齐"，交给渲染循环 */
const pendingAlign = shallowRef(null)
let aligned = false

watch(
  state,
  (g) => {
    if (g && !modelScene.value) {
      /* 归一化：居中 + 落地 + 阴影（不传 size——最长边缩放会把坐深当基准压矮高度） */
      normalizeModel(g, { shadow: true })
      /* 先定朝向，使后续"测屁股位置"反映旋转后的真实水平方向 */
      g.rotation.y = SEAT_ROT_Y
      /* 临时按高度缩放到 TARGET_SEAT_H（椅子就绪后 onRender 会按椅背顶重缩纠正） */
      g.updateMatrixWorld(true)
      let box = new Box3().setFromObject(g)
      const rawH = box.getSize(new Vector3()).y || 1
      g.scale.multiplyScalar(TARGET_SEAT_H / rawH)
      /* 缩放后重新落地：黑盒测缩放后 min.y 补偿，保证脚踩地 */
      g.updateMatrixWorld(true)
      box = new Box3().setFromObject(g)
      g.position.y -= box.min.y
      modelScene.value = g
      anims.value = g.animations || []
      /* 尺度/水平对齐交给渲染循环（要等椅子也加载完），这里只登记待对齐 */
      aligned = false
      pendingAlign.value = g
      setDiag('loaded, wait chair+align')
    }
  },
  { immediate: true },
)

watch(
  error,
  (e) => {
    if (e) {
      loadError.value = true
      setDiag('FBX err: ' + (e && e.message ? e.message : e))
      console.warn('[worker] FBX load failed', props.workerId, e)
    }
  },
  { immediate: true },
)

/* 坐动画：useAnimations 响应式绑定 modelScene（异步就绪后自动重建 mixer/actions），
   自带每帧 onBeforeRender update；就绪后播放第一条 clip（Mixamo 单动作下载即坐动画） */
const { actions } = useAnimations(anims, modelScene)
watch(anims, () => {
  nextTick(() => {
    const first = actions[Object.keys(actions)[0]]
    first?.reset().play()
  })
})

/* ══ 胳膊抬升：在 useAnimations 的 onBeforeRender(update) 之后注册，故每帧先 update 动画再覆盖胳膊 ══ */
const { onRender, onBeforeRender } = useLoop()
let armL = null
let armR = null
onBeforeRender(() => {
  const g = modelScene.value
  if (!g) return
  /* 懒找并缓存左右大臂骨骼（HMR 重载会重置为 null 重新找） */
  if (!armL) {
    armL = findBone(g, 'LeftArm')
    armR = findBone(g, 'RightArm')
  }
  /* 动画本帧已把 rotation 设为 pose 值，此处减 ARM_RAISE 即"在动画姿势上抬一点"，下帧 update 会重置不累加 */
  if (armL) armL.rotation.x -= ARM_RAISE
  if (armR) armR.rotation.x -= ARM_RAISE
})

/* a 是否为 b 的祖先（用于把含 'Chair' 的零件去重为椅子根） */
function isAncestor(a, b) {
  let p = b.parent
  while (p) {
    if (p === a) return true
    p = p.parent
  }
  return false
}

/* ══ 运行时自动对齐：每帧查场景里的椅子，就绪后按椅背顶定尺度 + 屁股钉最近椅子，一次即停 ══ */
const { camera } = useTres()
onRender(() => {
  /* 每个早退分支都写面板，确保"没生效"时也能从截图看见卡在哪一步 */
  if (aligned) return /* 已对齐：面板保留上次跑通的值，不刷屏 */
  if (!pendingAlign.value) {
    setDiag('wait-pending (model未loaded?)')
    return
  }
  const cam = camera.value?.__tres?.object ?? camera.value
  if (!cam) {
    setDiag('cam:null (useTres未就绪)')
    return
  }
  /* 由相机上溯到场景根（绕开 useTres 是否暴露 scene 的不确定，camera 已证实可用） */
  let scene = cam
  while (scene.parent) scene = scene.parent
  /* 收集所有含 'Chair' 的节点，再去重为椅子根（零件名也含 Chair，全量量会拆成 N 块污染测量） */
  const chairNodes = []
  scene.traverse((n) => {
    if (n.name && n.name.includes('Chair')) chairNodes.push(n)
  })
  const roots = chairNodes.filter((n) => !chairNodes.some((o) => o !== n && isAncestor(o, n)))
  const chairs = roots.map((n) => {
    const cb = new Box3().setFromObject(n)
    return { w: n.getWorldPosition(new Vector3()), minY: cb.min.y, maxY: cb.max.y }
  })
  if (chairs.length === 0) {
    setDiag(`chairs:0 (raw Chair节点=${chairNodes.length})`)
    return
  }
  const g = pendingAlign.value
  /* 选水平上离本工位最近的椅子根 */
  const myX = props.position[0]
  const myZ = props.position[2]
  let best = chairs[0]
  let bestD = Infinity
  for (const c of chairs) {
    const d = (c.w.x - myX) ** 2 + (c.w.z - myZ) ** 2
    if (d < bestD) {
      bestD = d
      best = c
    }
  }
  /* ── 尺度：实测整椅椅背顶驱动；人头目标 = 椅背顶 × SEAT_HEAD_RATIO ── */
  g.updateMatrixWorld(true)
  let gbox = new Box3().setFromObject(g)
  const curH = gbox.getSize(new Vector3()).y || 1
  const targetH = best.maxY * SEAT_HEAD_RATIO
  g.scale.multiplyScalar(targetH / curH)
  /* 重缩后落地：脚踩地（ratio 取对时屁股因坐姿比例自然≈座面） */
  g.updateMatrixWorld(true)
  gbox = new Box3().setFromObject(g)
  g.position.y -= gbox.min.y
  /* ── 水平：屁股骨骼钉到最近椅子（getWorldPosition 已含工位位移，差值直接补到局部 position） ── */
  const hips = findBone(g, 'Hips')
  if (hips) {
    g.updateMatrixWorld(true)
    const hipW = hips.getWorldPosition(new Vector3())
    g.position.x += best.w.x - hipW.x
    g.position.z += best.w.z - hipW.z
  }
  aligned = true
  pendingAlign.value = null
  /* 面板+console 双写跑通数字：含手高 leftHandY 与估算桌面高 deskY，胳膊没搭准时据此精调 ARM_RAISE */
  g.updateMatrixWorld(true)
  const ab = new Box3().setFromObject(g)
  const hipY = hips ? hips.getWorldPosition(new Vector3()).y : -1
  const leftHand = findBone(g, 'LeftHand')
  const leftHandY = leftHand ? leftHand.getWorldPosition(new Vector3()).y : -1
  const f2 = (n) => +n.toFixed(2)
  setDiag(
    `aligned | chairTopY=${f2(best.maxY)} targetH=${f2(targetH)} headY=${f2(ab.max.y)} ` +
    `hipY=${f2(hipY)} leftHandY=${f2(leftHandY)} deskY≈${f2(hipY + 0.3)} ` +
    `roots=${chairs.length} ratio=${SEAT_HEAD_RATIO} armRaise=${ARM_RAISE}`,
  )
  console.log('[worker aligned]', props.workerId, diag.value)
})

/* ══ 交互：悬浮缩放 + 光标 + 点击（事件从子网格冒泡到根分组） ══ */
const hovered = ref(false)
function onOver() {
  hovered.value = true
  document.body.style.cursor = 'pointer'
}
function onOut() {
  hovered.value = false
  document.body.style.cursor = 'auto'
}
function onClick() {
  emit('select', props.workerId)
}
</script>

<template>
  <!-- 根分组：承载整体悬浮缩放与指针事件；position 与工位一致，坐姿对齐在模型本地施加 -->
  <TresGroup
    :position="position"
    :scale="hovered ? [1.05, 1.05, 1.05] : [1, 1, 1]"
    @click="onClick"
    @pointer-over="onOver"
    @pointer-out="onOut"
  >
    <!-- 加载成功：渲染 glTF 坐姿人（阴影已由 normalizeModel 在遍历中开启） -->
    <primitive v-if="modelScene" :object="modelScene" />

    <!-- 兜底：加载中 / 加载失败 都显示原几何体人，永不闪空白；手臂固定前伸呈打字姿态（静态） -->
    <template v-else>
      <!-- 躯干 -->
      <TresMesh :position="[0, 0.86, 0.55]" cast-shadow>
        <TresBoxGeometry :args="[0.3, 0.5, 0.2]" />
        <TresMeshStandardMaterial :color="shirt" :roughness="0.8" />
      </TresMesh>
      <!-- 头部 -->
      <TresMesh :position="[0, 1.24, 0.55]" cast-shadow>
        <TresSphereGeometry :args="[0.14, 20, 20]" />
        <TresMeshStandardMaterial :color="SKIN" :roughness="0.7" />
      </TresMesh>
      <!-- 左臂（固定前伸） -->
      <TresGroup :position="[-0.19, 1.02, 0.52]">
        <TresMesh :position="[0, -0.1, -0.2]" :rotation="[0.7, 0, 0]" cast-shadow>
          <TresBoxGeometry :args="[0.07, 0.07, 0.4]" />
          <TresMeshStandardMaterial :color="shirt" :roughness="0.8" />
        </TresMesh>
      </TresGroup>
      <!-- 右臂（固定前伸） -->
      <TresGroup :position="[0.19, 1.02, 0.52]">
        <TresMesh :position="[0, -0.1, -0.2]" :rotation="[0.7, 0, 0]" cast-shadow>
          <TresBoxGeometry :args="[0.07, 0.07, 0.4]" />
          <TresMeshStandardMaterial :color="shirt" :roughness="0.8" />
        </TresMesh>
      </TresGroup>
      <!-- 大腿 -->
      <TresMesh :position="[-0.1, 0.48, 0.36]" cast-shadow>
        <TresBoxGeometry :args="[0.1, 0.1, 0.34]" />
        <TresMeshStandardMaterial :color="PANTS" :roughness="0.85" />
      </TresMesh>
      <TresMesh :position="[0.1, 0.48, 0.36]" cast-shadow>
        <TresBoxGeometry :args="[0.1, 0.1, 0.34]" />
        <TresMeshStandardMaterial :color="PANTS" :roughness="0.85" />
      </TresMesh>
      <!-- 小腿 -->
      <TresMesh :position="[-0.1, 0.26, 0.2]" cast-shadow>
        <TresBoxGeometry :args="[0.09, 0.36, 0.09]" />
        <TresMeshStandardMaterial :color="PANTS" :roughness="0.85" />
      </TresMesh>
      <TresMesh :position="[0.1, 0.26, 0.2]" cast-shadow>
        <TresBoxGeometry :args="[0.09, 0.36, 0.09]" />
        <TresMeshStandardMaterial :color="PANTS" :roughness="0.85" />
      </TresMesh>
    </template>
  </TresGroup>
</template>
