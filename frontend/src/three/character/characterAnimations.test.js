/* ═══════════════════════════════════════════
   characterAnimations 测试
   断言：返回全部 8 个动作 clip；
   walk 含 Hips.position track；idleStand 含 Head.quaternion track；
   末尾 real-three 集成测试：真实 AnimationMixer 下动画真的转动骨骼（C1 回归）
   ═══════════════════════════════════════════ */
import { describe, it, expect } from 'vitest'
import { AnimationClip } from 'three'
import { createAnimations } from './characterAnimations'
import { buildCharacter } from './buildCharacter'

describe('createAnimations', () => {
  it('返回全部动作 clip', () => {
    const anims = createAnimations()
    const keys = ['idleStand', 'walk', 'sit', 'standUp', 'sitIdle', 'talk', 'wave', 'reactClick']
    for (const k of keys) {
      expect(anims[k]).toBeInstanceOf(AnimationClip)
    }
  })

  it('walk 在 Hips 上有 position track', () => {
    const { walk } = createAnimations()
    const hasPos = walk.tracks.some((t) => t.name.includes('Hips.position'))
    expect(hasPos).toBe(true)
  })

  it('idleStand 在 Head 上有 quaternion track（C1：姿态轨道直写四元数）', () => {
    const { idleStand } = createAnimations()
    const hasRot = idleStand.tracks.some((t) => t.name.includes('Head.quaternion'))
    expect(hasRot).toBe(true)
  })

  it('所有 track 的 values 长度 = times 长度 × valueSize（防 keyframe length mismatch）', () => {
    const anims = createAnimations()
    for (const anim of Object.values(anims)) {
      for (const track of anim.tracks) {
        expect(track.values.length).toBe(track.times.length * track.getValueSize())
      }
    }
  })
})

/* ═══════════════════════════════════════════
   real-three 集成测试（C1 回归）
   用真实 three AnimationMixer（非 fake 桩）播放 idleStand 0.5s，
   断言骨骼 quaternion 非恒等 —— 证明姿态轨道真的转动骨骼。
   修复前 rotTrack 用 `.rotation`（Euler），PropertyBinding 经 Euler.fromArray
   把四元数 w 写进 _order，setFromEuler 落 unknown order，骨骼不动，此测试为红。
   ═══════════════════════════════════════════ */
describe('createAnimations × buildCharacter（real-three 集成，C1 回归）', () => {
  it('idleStand 播放 0.5s 后 Head/Chest 骨骼 quaternion 非恒等', () => {
    const { group, mixer } = buildCharacter({ gender: 'male', shirtColor: '#9CC7E8' })
    const animations = createAnimations()

    const head = group.getObjectByName('Head')
    const chest = group.getObjectByName('Chest')
    expect(head).toBeTruthy()
    expect(chest).toBeTruthy()
    // 初始姿态：quaternion 应为恒等（x=y=z=0, w=1）
    expect(head.quaternion.x).toBeCloseTo(0, 6)
    expect(head.quaternion.w).toBeCloseTo(1, 6)

    // 真实 mixer 播放 idleStand 并推进 0.5s。
    // idleStand Head 轨道 [0,0.5,1]s → q(0,0,0) / q(0.04,0,0) / q(0,0,0)，
    // t=0.5 处即绕 X 转 0.04rad：x=sin(0.02)≈0.02, w=cos(0.02)≈0.9998
    const action = mixer.clipAction(animations.idleStand)
    action.reset().play()
    mixer.update(0.5)

    // Head 转动：x 分量非零（≈0.02），w 从 1 降至 ≈0.9998
    expect(head.quaternion.x).not.toBeCloseTo(0, 6)
    expect(Math.abs(head.quaternion.x)).toBeGreaterThan(0.01)
    expect(head.quaternion.w).toBeCloseTo(Math.cos(0.02), 4)
    // Chest 轨道同播（q(0.03,0,0)）：x≈0.015 非零
    expect(Math.abs(chest.quaternion.x)).toBeGreaterThan(0.01)
  })
})
