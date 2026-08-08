<script setup>
/* ═══════════════════════════════════════════
   OfficeWorker —— 工作人员（自研骨骼化人物）
   用 buildCharacter 构建风格化人物 + 状态机驱动
   替代原 useFBX 加载 Mixamo 坐姿模型
   交互：点击上抛 select；悬停挥手+看镜头+手形光标
   位置：charGroup 承载工位坐标（世界坐标语义），TresGroup 仅作事件容器
   ═══════════════════════════════════════════ */
import { ref, shallowRef, onMounted } from 'vue'
import { Group, LoopOnce } from 'three'
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
  mixer = built.mixer
  const animations = createAnimations()
  /* 跨任务决策 1（faceToward 假设模型面朝 +Z，实测 buildCharacter 脸朝 -Z）：
     内层 built.group 固定绕 Y 180° 把几何脸转到 +Z；外层 charGroup 由状态机驱动
     （位移 + 朝向），保证 faceToward 的 forward(+Z) 与脸方向一致，且位移为世界坐标 */
  const charGroup = new Group()
  built.group.rotation.y = Math.PI
  charGroup.add(built.group)
  charGroup.position.set(props.position[0], 0, props.position[2])
  motion = createMotionController({
    group: charGroup,
    mixer,
    animations,
    speed: 0.8,
  })
  /* 跨任务决策 2（一次性动画 LoopOnce）：wave/reactClick/sit/standUp 播完停末帧；
     Task 4 的 playClip 每次 play 前 reset，故重复触发可正常重播 */
  for (const n of ['wave', 'reactClick', 'sit', 'standUp']) {
    mixer.clipAction(animations[n]).setLoop(LoopOnce, 1)
  }
  /* 先播放 idleStand */
  mixer.clipAction(animations.idleStand).reset().play()
  char.value = charGroup
}
onMounted(ensureBuilt)

/* 每帧推进状态机 */
onRender(({ delta }) => {
  if (mixer && motion) motion.update(delta)
})

/* 交互 */
const hovered = ref(false)
function onOver() {
  hovered.value = true
  document.body.style.cursor = 'pointer'
  // 悬停：挥手 + 看镜头（talk 循环姿态）
  if (motion) motion.setState('talk')
}
function onOut() {
  hovered.value = false
  document.body.style.cursor = 'auto'
  if (motion) motion.setState('idle')
}
function onClick() {
  // 播打招呼动画（LoopOnce 一次性）+ 立即上抛 select（路由跳转交给上层）
  if (motion) motion.setState('standUp')
  emit('select', props.workerId)
}

/* 暴露给 OfficeScene：会谈调度驱动工人走向目标（世界坐标） */
function walkTo(x, z) {
  if (motion) motion.walkTo(x, z)
}
defineExpose({ walkTo })
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
