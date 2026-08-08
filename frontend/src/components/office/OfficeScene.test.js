/* ═══════════════════════════════════════════
   OfficeScene 测试
   验证场景组合根组件渲染两个工位名牌 + 会谈调度链路
   （walkTo 走向中央 → 3 轮对话 → 回工位坐下）
   mock @tresjs/core（TresCanvas 用简单渲染函数 stub）
   ═══════════════════════════════════════════ */
import { describe, it, expect, vi, beforeAll, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import OfficeScene from './OfficeScene.vue'

afterEach(() => {
  vi.useRealTimers()
})

/* happy-dom 的 canvas.getContext('2d') 返回 null，名牌/大屏/装饰都靠 Canvas 生成贴图，
   补一个最小 2d context 让贴图生成逻辑不崩（仅验证场景组合渲染） */
beforeAll(() => {
  HTMLCanvasElement.prototype.getContext = vi.fn(() => ({
    fillStyle: null, strokeStyle: null, lineWidth: 0, font: null,
    textAlign: null, textBaseline: null, lineCap: null,
    fillRect: vi.fn(), strokeRect: vi.fn(), clearRect: vi.fn(),
    fillText: vi.fn(), strokeText: vi.fn(),
    measureText: () => ({ width: 0 }),
    beginPath: vi.fn(), moveTo: vi.fn(), lineTo: vi.fn(), stroke: vi.fn(),
    fill: vi.fn(), ellipse: vi.fn(), arc: vi.fn(), roundRect: vi.fn(),
    save: vi.fn(), restore: vi.fn(), translate: vi.fn(), rotate: vi.fn(),
    drawImage: vi.fn(), createLinearGradient: () => ({ addColorStop: vi.fn() }),
  }))
})

vi.mock('@tresjs/core', () => ({
  // TresCanvas stub 需透传渲染 slot 内容，否则名牌/装饰等子组件不渲染，文本断言恒空
  TresCanvas: { inheritAttrs: false, setup: (_, ctx) => () => ctx.slots.default?.() },
  useTres: () => ({ camera: { value: null } }),
  useLoop: () => ({ onRender: vi.fn() }),
}))
vi.mock('@tresjs/cientos', async () => {
  const { Object3D } = await import('three')
  const { ref } = await import('vue')
  return {
    OrbitControls: { inheritAttrs: false, setup: () => () => {} },
    // useGLTF 返回 { state, error }：state 出现 scene 即视为加载成功（useModel 用 watch 监听）
    useGLTF: () => ({ state: ref({ scene: new Object3D() }), error: ref(null) }),
  }
})

describe('OfficeScene', () => {
  it('渲染两个工位', () => {
    // happy-dom 无 canvas 2d 上下文，OfficeNameplate 需生成贴图 → stub 为纯文本
    // 仍断言 text 传入正确，验证场景组合把两个名牌接进模板
    const wrapper = mount(OfficeScene, {
      global: {
        stubs: {
          OfficeNameplate: { props: ['text'], template: '<div>{{ text }}</div>' },
        },
      },
    })
    expect(wrapper.text()).toContain('AI 前沿')
    expect(wrapper.text()).toContain('股票分析')
  })

  it('会谈调度：定时触发 walkTo 走向中央，3 轮后回工位并坐下', () => {
    // F2：用假时钟驱动调度，workers stub 暴露 walkTo/sitDown
    // stub 的 walkTo 同步触发到达回调，模拟"走回工位后坐下"链路
    vi.useFakeTimers()
    const wrapper = mount(OfficeScene, {
      global: {
        stubs: {
          OfficeNameplate: { props: ['text'], template: '<div>{{ text }}</div>' },
          OfficeWorker: {
            props: ['position', 'workerId'],
            setup() {
              const walkTo = vi.fn((_x, _z, cb) => cb?.())
              const sitDown = vi.fn()
              return { walkTo, sitDown }
            },
            template: '<div />',
          },
          CharacterBubble: {
            setup() { return { show: vi.fn() } },
            template: '<div />',
          },
        },
      },
    })
    // 模板 ref 收集的工人实例
    const aiNews = wrapper.vm.$refs.ai_news
    const stock = wrapper.vm.$refs.stock
    expect(aiNews).toBeTruthy()
    expect(stock).toBeTruthy()

    // 4s 后首轮会谈：两人走向中央会谈区
    vi.advanceTimersByTime(4000)
    expect(aiNews.walkTo).toHaveBeenCalledWith(0, -0.5)
    expect(stock.walkTo).toHaveBeenCalledWith(1.2, -0.5)

    // 3 轮对话（每轮 2s）：6s 后会谈结束 → 各自走回工位，到达回调触发坐下
    vi.advanceTimersByTime(6000)
    expect(aiNews.walkTo).toHaveBeenCalledWith(-3, -2, expect.any(Function))
    expect(stock.walkTo).toHaveBeenCalledWith(3, -2, expect.any(Function))
    expect(aiNews.sitDown).toHaveBeenCalledTimes(1)
    expect(stock.sitDown).toHaveBeenCalledTimes(1)

    wrapper.unmount()
  })
})
