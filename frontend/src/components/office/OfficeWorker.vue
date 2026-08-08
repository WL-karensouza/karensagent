<script setup>
/* ═══════════════════════════════════════════
   OfficeWorker —— 工作人员（自研骨骼化人物）
   用 buildCharacter 构建风格化人物 + 状态机驱动
   替代原 useFBX 加载 Mixamo 坐姿模型
   交互：点击上抛 select；悬停挥手+看镜头+手形光标
   位置：built.group 承载工位坐标（世界坐标语义），TresGroup 仅作事件容器
   ═══════════════════════════════════════════ */
import { shallowRef, onMounted } from 'vue'
import { LoopOnce } from 'three'
import { useLoop } from '@tresjs/core'
import { buildCharacter } from '../../three/character/buildCharacter'
import { createAnimations } from '../../three/character/characterAnimations'
import { createMotionController } from '../../three/character/useCharacterMotion'

const props = defineProps({
  /* 工位位置 [x, y, z]（与对应办公桌一致） */
  position: { type: Array, default: () => [0, 0, 0] },
  /* Agent id：ai_news | stock */
  workerId: { type: String, default: 'ai_news' },
})

/* 点击上抛给 OfficeScene，本组件不碰 router；bubble 供 OfficeScene 气泡层调用 */
const emit = defineEmits(['select', 'bubble'])

/* 主题色：男士浅蓝 / 女士橙色（王磊哥哥拍板） */
const GENDER = props.workerId === 'stock' ? 'female' : 'male'
const SHIRT = props.workerId === 'stock' ? '#D97706' : '#9CC7E8'

/* 自建角色 */
const char = shallowRef(null) // 角色 group（禁深代理）
let mixer = null
let motion = null
const { onRender } = useLoop()

/* 构建角色（组件挂载后执行） */
function ensureBuilt() {
  if (char.value) return
  const built = buildCharacter({ gender: GENDER, shirtColor: SHIRT })
  /* 脸部朝向已由 buildCharacter 修正为 +Z（headMesh/hairMesh 局部转 π），
     built.group 保持不转，walk 骨骼位移（局部 +Z）与 faceToward 前进方向一致 */
  built.group.position.set(props.position[0], 0, props.position[2])
  mixer = built.mixer
  const animations = createAnimations()
  motion = createMotionController({
    group: built.group,
    mixer,
    animations,
    speed: 0.8,
  })
  /* 跨任务决策 2（一次性动画 LoopOnce）：wave/reactClick/sit/standUp 播完停末帧；
     clampWhenFinished=true（C2 修复）：只设 LoopOnce 时 three r179 播完
     enabled=false 会恢复 bind pose（坐姿弹回站立），clamp 后保持末帧坐姿/挥手位；
     Task 4 的 playClip 每次 play 前 reset，故重复触发可正常重播 */
  for (const n of ['wave', 'reactClick', 'sit', 'standUp']) {
    const act = mixer.clipAction(animations[n]).setLoop(LoopOnce, 1)
    act.clampWhenFinished = true
  }
  /* 先播放 idleStand */
  mixer.clipAction(animations.idleStand).reset().play()
  char.value = built.group
}
onMounted(ensureBuilt)

/* 每帧推进状态机 */
onRender(({ delta }) => {
  if (mixer && motion) motion.update(delta)
})

/* 交互 */
function onOver() {
  document.body.style.cursor = 'pointer'
  // 悬停：挥手（wave 一次性动画，LoopOnce 播完停末帧挥手位）
  if (motion) motion.setState('wave')
}
function onOut() {
  document.body.style.cursor = 'auto'
  if (motion) motion.setState('idle')
}
function onClick() {
  // 王磊哥哥拍板：点击立即跳转（无延迟），打招呼动画不可见故不再播放
  emit('select', props.workerId)
}

/* 暴露给 OfficeScene：会谈调度驱动工人走向目标（世界坐标）；
   onArrive：到达目标后的回调（会谈结束回工位后坐下） */
function walkTo(x, z, onArrive) {
  if (motion) motion.walkTo(x, z, onArrive)
}
/* 到达工位后坐下：落座（sit 一次性）+ 打字循环（sitIdle 叠加） */
function sitDown() {
  if (motion) motion.sitDown()
}
defineExpose({ walkTo, sitDown })
</script>

<template>
  <TresGroup
    @click="onClick"
    @pointer-over="onOver"
    @pointer-out="onOut"
  >
    <primitive v-if="char" :object="char" />
  </TresGroup>
</template>
