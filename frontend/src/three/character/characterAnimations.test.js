/* ═══════════════════════════════════════════
   characterAnimations 测试
   断言：返回全部 8 个动作 clip；
   walk 含 Hips.position track；idleStand 含 Head.rotation track
   ═══════════════════════════════════════════ */
import { describe, it, expect } from 'vitest'
import { AnimationClip } from 'three'
import { createAnimations } from './characterAnimations'

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

  it('idleStand 在 Head 上有 rotation track（用于眨眼/点头）', () => {
    const { idleStand } = createAnimations()
    const hasRot = idleStand.tracks.some((t) => t.name.includes('Head.rotation'))
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
