/* ═══════════════════════════════════════════
   useCharacterMotion 测试
   使用最小假对象驱动，验证走/停/切姿态链路
   ═══════════════════════════════════════════ */
import { describe, it, expect, vi } from 'vitest'
import { createMotionController } from './useCharacterMotion'

// 最小假对象：模拟 buildCharacter 产物
function fakeChar() {
  const group = { position: { x: 0, z: 0 }, quaternion: { slerp: vi.fn() } }
  const mixer = {
    update: vi.fn(),
    // clipAction 做成 spy 并返回 action 对象，可断言"取了哪个 clip"
    clipAction: vi.fn(() => ({ play: vi.fn(), fadeIn: vi.fn(), fadeOut: vi.fn(), stop: vi.fn() })),
    stopAllAction: vi.fn(),
  }
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

  it('setState wave 播放挥手 clip 并进入 WAVE 态（F1 悬停）', () => {
    const f = fakeChar()
    const c = createMotionController({ ...f, speed: 1 })
    expect(() => c.setState('wave')).not.toThrow()
    expect(c.state).toBe('WAVE')
  })

  it('walkTo 到达后触发单次到达回调（会谈回工位后坐下）', () => {
    const arrive = vi.fn()
    const c = createMotionController({ ...fakeChar(), speed: 100 })
    c.walkTo(0.1, 0, arrive)
    c.update(0.5, 0)
    expect(arrive).toHaveBeenCalledTimes(1)
    // 单次触发：到达后回调即清除，后续 update 不再重放
    c.update(0.5, 0)
    expect(arrive).toHaveBeenCalledTimes(1)
  })

  it('sitDown 播 sit 主姿态并叠加 sitIdle 打字循环', () => {
    const f = fakeChar()
    const c = createMotionController({ ...f, speed: 1 })
    c.sitDown()
    expect(c.state).toBe('SIT')
    // sit 与 sitIdle 都被取来播放
    expect(f.mixer.clipAction).toHaveBeenCalledWith(f.animations.sit)
    expect(f.mixer.clipAction).toHaveBeenCalledWith(f.animations.sitIdle)
  })
})
