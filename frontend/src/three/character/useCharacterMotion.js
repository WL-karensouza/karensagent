/* ═══════════════════════════════════════════
   useCharacterMotion —— 人物运动状态机
   状态：IDLE / WALK / SIT / STAND_UP / TALK / WAVE
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
  wave: 'WAVE',
}

export function createMotionController({ group, mixer, animations, waypoints = [], speed = 1, onReachWaypoint = null }) {
  let state = 'IDLE'
  let target = null           // { x, z } 待到达目标点
  let action = null           // 当前播放的 mixer action
  let overlayAction = null    // 坐姿打字叠加层（sitDown 专用，与主姿态并行，不冲突）
  let onArrive = null         // walkTo 单次到达回调（会谈回工位后坐下用）
  const forward = new Vector3(0, 0, 1) // 人物默认朝向（buildCharacter 模型面朝 +Z）

  /* 播放某 clip，可选淡入时长
     分步调用兼容 fake（vi.fn() 无链式返回值）；
     reset?.() 可选调用：真实 three AnimationAction 二次播放一次性动画
     （wave/reactClick）必须先 reset 才能从头播，fake 无 reset 也不崩
     切主姿态前先停掉坐姿打字叠加层，避免残留 */
  function playClip(name, fadeIn = 0.2) {
    if (overlayAction) { overlayAction.stop(); overlayAction = null }
    if (action) action.fadeOut(0.1)
    const next = mixer.clipAction(animations[name])
    next.reset?.()
    next.fadeIn(fadeIn)
    next.play()
    action = next
  }

  /* 手动切换姿态（入参小写，内部统一为大写常量） */
  function setState(next) {
    const s = STATE_MAP[next]
    if (s == null) {
      // 未知姿态（如误传大写）静默忽略，打日志便于排查
      console.warn(`[useCharacterMotion] 未知姿态: ${next}，忽略`)
      return
    }
    if (state === s) return
    state = s
    switch (s) {
      case 'IDLE': playClip('idleStand'); break
      case 'WALK': playClip('walk'); break
      case 'SIT': playClip('sit'); break
      case 'STAND_UP': playClip('standUp'); break
      case 'TALK': playClip('talk'); break
      case 'WAVE': playClip('wave'); break
    }
  }

  /* 设置目标点并进入 WALK 状态；
     onArrive：到达目标时回调（会谈结束回工位后坐下用），单次生效 */
  function walkTo(x, z, arrive) {
    target = { x, z }
    onArrive = arrive
    setState('walk')
  }

  /* 坐下：先播一次性 sit 落座，再叠加 sitIdle 打字循环
     （sit 只转 Hips/Spine/UpperLeg，sitIdle 只转 LowerArm，两者骨骼不重叠，
     叠加播放不会互相覆盖；sit 由 OfficeWorker 设为 LoopOnce 停末帧保持坐姿）
     直接置 SIT 态而非走 setState：避免同态提前 return，重复调用也能重播落座 */
  function sitDown() {
    state = 'SIT'
    playClip('sit')
    const overlay = mixer.clipAction(animations.sitIdle)
    overlay.reset?.()
    overlay.play()
    overlayAction = overlay
  }

  /* 原地平滑转向目标：slerp 朝目标插值，t 为插值系数（默认缓慢收敛，
     传 1 则一步精确对齐）。需在移动/落位前调用，避免 dx/dz 归零） */
  function faceToward(x, z, t = 0.15) {
    const dx = x - group.position.x
    const dz = z - group.position.z
    if (Math.hypot(dx, dz) < EPS) return
    const targetQ = new Quaternion().setFromUnitVectors(forward, new Vector3(dx, 0, dz).normalize())
    group.quaternion.slerp(targetQ, t)
  }

  /* 是否在走动：处于 WALK 状态或仍持有未到达目标 */
  function isMoving() {
    return state === 'WALK' || target != null
  }

  /* 每帧驱动：推进 mixer + 处理走向目标的移动/转向（time 供消费方传全局时钟，暂未使用） */
  function update(delta, time) {
    mixer.update(delta, time)

    if (!target) return

    const dx = target.x - group.position.x
    const dz = target.z - group.position.z
    const dist = Math.hypot(dx, dz)

    // 已到达（或移动不超过目标点，clamp 落地）
    const step = speed * delta
    if (dist < EPS || dist <= step) {
      // 到达即清 target 前先精确对齐朝向（t=1），
      // 避免背对目标一步到达时从未转向（I-1 修复）
      faceToward(target.x, target.z, 1)
      group.position.x = target.x
      group.position.z = target.z
      target = null
      setState('idle')
      onReachWaypoint?.()
      // 单次到达回调（会谈回工位后坐下），触发后即失效
      const cb = onArrive
      onArrive = null
      cb?.()
      return
    }

    // 平滑转向 + 匀速前进
    faceToward(target.x, target.z)
    group.position.x += (dx / dist) * step
    group.position.z += (dz / dist) * step
  }

  return {
    group, // 暴露 group 引用，测试与消费方可直接读写位置
    update, walkTo, setState, faceToward, isMoving, sitDown,
    get state() { return state },
  }
}
