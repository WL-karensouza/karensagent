/* ═══════════════════════════════════════════
   useCharacterMotion 测试
   使用最小假对象驱动，验证走/停/切姿态链路
   ═══════════════════════════════════════════ */
import { describe, it, expect, vi } from 'vitest'
import { createMotionController } from './useCharacterMotion'

// 最小假对象：模拟 buildCharacter 产物
function fakeChar() {
  const group = { position: { x: 0, z: 0 }, quaternion: { slerp: vi.fn() } }
  const mixer = { update: vi.fn(), clipAction: () => ({ play: vi.fn(), fadeIn: vi.fn(), fadeOut: vi.fn(), stop: vi.fn() }), stopAllAction: vi.fn() }
  const skeleton = { bones: [] }
  const animations = { idleStand: {}, walk: {}, sit: {}, standUp: {}, sitIdle: {}, talk: {}, wave: {}, reactClick: {} }
  return { group, skeleton, mixer, animations }
}

describe('createMotionController', () => {
  it('walkTo 后 isMoving 为真，update 推进位置', () => {
    const c = createMotionController({ ...fakeChar(), waypoints: [], speed: 1 })
    c.walkTo(3, 0)
    expect(c.isMoving()).toBe(true)
    c.update(0.1, 0)
    expect(c.group.position.x).not.toBe(0)
  })

  it('到达目标点后停止移动', () => {
    const c = createMotionController({ ...fakeChar(), waypoints: [], speed: 100 })
    c.walkTo(0.1, 0) // 极近目标
    c.update(0.5, 0)
    expect(c.isMoving()).toBe(false)
  })

  it('setState 切换空闲不报错', () => {
    const c = createMotionController(fakeChar())
    expect(() => c.setState('idle')).not.toThrow()
  })

  it('到达目标后触发 onReachWaypoint 且完成转向对齐', () => {
    const onReachWaypoint = vi.fn()
    const f = fakeChar()
    const c = createMotionController({ ...f, waypoints: [], speed: 100, onReachWaypoint })
    c.walkTo(0.1, 0) // 极近目标
    c.update(0.5, 0)
    expect(onReachWaypoint).toHaveBeenCalledTimes(1)
    // 落位前应有一次 slerp 转向对齐（I-1 修复）
    expect(f.group.quaternion.slerp).toHaveBeenCalled()
  })
})
