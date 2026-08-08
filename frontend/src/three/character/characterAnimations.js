/* ═══════════════════════════════════════════
   characterAnimations —— 手写人物动画 clip
   姿态类：骨骼 rotation 关键帧（四元数，无万向锁）
   位移类：Hips.position 关键帧（如 walk 前进）
   一次性语义（wave/reactClick/sit/standUp）由消费方
   （Task 4 状态机）用 action.setLoop(THREE.LoopOnce, 1) 控制；
   three r179 的 AnimationClip 已无 loop 属性，故本文件不设置。
   ═══════════════════════════════════════════ */
import {
  AnimationClip, Quaternion, Euler, VectorKeyframeTrack, QuaternionKeyframeTrack,
} from 'three'

/* 便捷四元数：由欧拉角（弧度）构造 */
const q = (x, y, z) => new Quaternion().setFromEuler(new Euler(x, y, z))

/* 骨骼 rotation 单段轨迹（两端同一四元数，中间目标值） */
function rotTrack(name, times, quats) {
  return new QuaternionKeyframeTrack(`${name}.rotation`, times, quats.flatMap((e) => [e.x, e.y, e.z, e.w]))
}

export function createAnimations() {
  const DUR = 1.0 // 各动作基准时长（秒）

  // 站立呼吸：重心微沉 + 脊柱微前倾
  const idleStand = new AnimationClip('idleStand', DUR, [
    rotTrack('Hips', [0, 0.5, 1], [q(0, 0, 0), q(-0.02, 0, 0), q(0, 0, 0)]),
    rotTrack('Chest', [0, 0.5, 1], [q(0, 0, 0), q(0.03, 0, 0), q(0, 0, 0)]),
    rotTrack('Head', [0, 0.5, 1], [q(0, 0, 0), q(0.04, 0, 0), q(0, 0, 0)]),
  ])

  // 走路：双腿交替摆动 + 手臂对侧摆 + Hips 前移
  const walk = new AnimationClip('walk', 1.2, [
    new VectorKeyframeTrack('Hips.position', [0, 0.3, 0.6, 0.9, 1.2],
      [0, 0.95, 0, 0, 0.95, 0.12, 0, 0.95, 0.24, 0, 0.95, 0.12, 0, 0.95, 0]),
    rotTrack('LeftUpperLeg', [0, 0.6, 1.2], [q(0.6, 0, 0), q(-0.6, 0, 0), q(0.6, 0, 0)]),
    rotTrack('RightUpperLeg', [0, 0.6, 1.2], [q(-0.6, 0, 0), q(0.6, 0, 0), q(-0.6, 0, 0)]),
    rotTrack('LeftLowerLeg', [0, 0.6, 1.2], [q(-0.3, 0, 0), q(0.3, 0, 0), q(-0.3, 0, 0)]),
    rotTrack('RightLowerLeg', [0, 0.6, 1.2], [q(0.3, 0, 0), q(-0.3, 0, 0), q(0.3, 0, 0)]),
    rotTrack('LeftUpperArm', [0, 0.6, 1.2], [q(-0.5, 0, 0), q(0.5, 0, 0), q(-0.5, 0, 0)]),
    rotTrack('RightUpperArm', [0, 0.6, 1.2], [q(0.5, 0, 0), q(-0.5, 0, 0), q(0.5, 0, 0)]),
    // 上身前倾：行走时躯干随步态轻微前倾（语义契约要求）
    rotTrack('Spine', [0, 0.6, 1.2], [q(0, 0, 0), q(0.08, 0, 0), q(0, 0, 0)]),
  ])

  // 坐下：髋后移下沉 + 脊柱前屈
  const sit = new AnimationClip('sit', 0.8, [
    rotTrack('Hips', [0, 0.8], [q(0, 0, 0), q(-0.2, 0, 0)]),
    rotTrack('Spine', [0, 0.8], [q(0, 0, 0), q(0.15, 0, 0)]),
    rotTrack('LeftUpperLeg', [0, 0.8], [q(0, 0, 0), q(-1.2, 0, 0)]),
    rotTrack('RightUpperLeg', [0, 0.8], [q(0, 0, 0), q(-1.2, 0, 0)]),
  ])

  // 起身：镜像 sit
  const standUp = new AnimationClip('standUp', 0.8, [
    rotTrack('Hips', [0, 0.8], [q(-0.2, 0, 0), q(0, 0, 0)]),
    rotTrack('Spine', [0, 0.8], [q(0.15, 0, 0), q(0, 0, 0)]),
    rotTrack('LeftUpperLeg', [0, 0.8], [q(-1.2, 0, 0), q(0, 0, 0)]),
    rotTrack('RightUpperLeg', [0, 0.8], [q(-1.2, 0, 0), q(0, 0, 0)]),
  ])

  // 坐姿打字：双手小幅度往复
  const sitIdle = new AnimationClip('sitIdle', 1.0, [
    rotTrack('LeftLowerArm', [0, 0.25, 0.5, 0.75, 1], [q(-0.4, 0, 0), q(-0.1, 0, 0), q(-0.4, 0, 0), q(-0.1, 0, 0), q(-0.4, 0, 0)]),
    rotTrack('RightLowerArm', [0, 0.25, 0.5, 0.75, 1], [q(-0.4, 0, 0), q(-0.1, 0, 0), q(-0.4, 0, 0), q(-0.1, 0, 0), q(-0.4, 0, 0)]),
  ])

  // 交谈：双手手势 + 点头
  const talk = new AnimationClip('talk', 1.4, [
    rotTrack('LeftUpperArm', [0, 0.7, 1.4], [q(-0.6, 0, 0.2), q(-0.8, 0, -0.2), q(-0.6, 0, 0.2)]),
    rotTrack('RightUpperArm', [0, 0.7, 1.4], [q(-0.6, 0, -0.2), q(-0.8, 0, 0.2), q(-0.6, 0, -0.2)]),
    rotTrack('Head', [0, 0.35, 0.7, 1.05, 1.4], [q(0.1, 0, 0), q(-0.05, 0, 0), q(0.1, 0, 0), q(-0.05, 0, 0), q(0.1, 0, 0)]),
  ])

  // 挥手（悬停反应，一次性）
  const wave = new AnimationClip('wave', 1.0, [
    rotTrack('RightUpperArm', [0, 0.15, 0.5, 0.85, 1], [q(0, 0, 0), q(-2.4, 0, -0.4), q(-2.4, 0, 0.3), q(-2.4, 0, -0.4), q(0, 0, 0)]),
  ])

  // 被点击打招呼（一次性，欠身+挥手）
  const reactClick = new AnimationClip('reactClick', 1.2, [
    rotTrack('Spine', [0, 0.3, 1.2], [q(0, 0, 0), q(0.2, 0, 0), q(0, 0, 0)]),
    rotTrack('RightUpperArm', [0, 0.2, 0.6, 1.0, 1.2], [q(0, 0, 0), q(-2.4, 0, -0.3), q(-2.4, 0, 0.3), q(-2.4, 0, -0.3), q(0, 0, 0)]),
  ])

  return { idleStand, walk, sit, standUp, sitIdle, talk, wave, reactClick }
}
