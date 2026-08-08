/* ═══════════════════════════════════════════
   useCharacterMotion —— 人物运动状态机
   状态：IDLE / WALK / SIT / STAND_UP / TALK
   移动：直线前进（clamp 不越过目标）+ 平滑转向（quaternion slerp）
   姿态：通过 mixer 播放对应 clip
   说明：简报 setState 传小写姿态名，内部状态统一存大写常量，
   isMoving 以 state === 'WALK' 或 target 存在为走动依据，链路自洽。
   ═══════════════════════════════════════════ */
import { Quaternion, Vector3 } from 'three'

const EPS = 1e-4

/* 姿态名 → 内部状态大写常量 */
const STATE_MAP = {
  idle: 'IDLE',
  walk: 'WALK',
  sit: 'SIT',
  standUp: 'STAND_UP',
  talk: 'TALK',
}

export function createMotionController({ group, mixer, animations, waypoints = [], speed = 1, onReachWaypoint = null }) {
  let state = 'IDLE'
  let target = null           // { x, z } 待到达目标点
  let action = null           // 当前播放的 mixer action
  const forward = new Vector3(0, 0, 1) // 人物默认朝向（buildCharacter 模型面朝 +Z）

  /* 播放某 clip，可选淡入时长（分步调用，兼容 vi.fn() 无链式返回值） */
  function playClip(name, fadeIn = 0.2) {
    if (action) action.fadeOut(0.1)
    const next = mixer.clipAction(animations[name])
    next.fadeIn(fadeIn)
    next.play()
    action = next
  }

  /* 手动切换姿态（入参小写，内部统一为大写常量） */
  function setState(next) {
    const s = STATE_MAP[next]
    if (s == null || state === s) return
    state = s
    switch (s) {
      case 'IDLE': playClip('idleStand'); break
      case 'WALK': playClip('walk'); break
      case 'SIT': playClip('sit'); break
      case 'STAND_UP': playClip('standUp'); break
      case 'TALK': playClip('talk'); break
    }
  }

  /* 设置目标点并进入 WALK 状态 */
  function walkTo(x, z) {
    target = { x, z }
    setState('walk')
  }

  /* 原地平滑转向目标（slerp 朝目标插值，多次调用逐渐收敛） */
  function faceToward(x, z) {
    const dx = x - group.position.x
    const dz = z - group.position.z
    if (Math.hypot(dx, dz) < EPS) return
    const targetQ = new Quaternion().setFromUnitVectors(forward, new Vector3(dx, 0, dz).normalize())
    group.quaternion.slerp(targetQ, 0.15)
  }

  /* 是否在走动：处于 WALK 状态或仍持有未到达目标 */
  function isMoving() {
    return state === 'WALK' || target != null
  }

  /* 每帧驱动：推进 mixer + 处理走向目标的移动/转向 */
  function update(delta) {
    mixer.update(delta)

    if (!target) return

    const dx = target.x - group.position.x
    const dz = target.z - group.position.z
    const dist = Math.hypot(dx, dz)

    // 已到达（或移动不超过目标点，clamp 落地）
    const step = speed * delta
    if (dist < EPS || dist <= step) {
      group.position.x = target.x
      group.position.z = target.z
      target = null
      setState('idle')
      onReachWaypoint?.()
      return
    }

    // 平滑转向 + 匀速前进
    faceToward(target.x, target.z)
    group.position.x += (dx / dist) * step
    group.position.z += (dz / dist) * step
  }

  return {
    group, // 暴露 group 引用，测试与消费方可直接读写位置
    update, walkTo, setState, faceToward, isMoving,
    get state() { return state },
  }
}
