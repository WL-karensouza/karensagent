/* ═══════════════════════════════════════════
   OfficeScene 测试
   验证场景组合根组件渲染两个工位名牌 + 点击名牌跳转（go-agent）
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

  it('点击名牌 → emit go-agent（点击进工位）', async () => {
    const wrapper = mount(OfficeScene, {
      global: {
        stubs: {
          OfficeNameplate: {
            name: 'OfficeNameplate',
            props: ['text'],
            emits: ['select'],
            template: '<div>{{ text }}</div>',
          },
        },
      },
    })
    const plates = wrapper.findAllComponents({ name: 'OfficeNameplate' })
    expect(plates).toHaveLength(2)

    // 点击 AI 前沿名牌 → 跳转 ai_news
    await plates.find((c) => c.props('text') === 'AI 前沿').vm.$emit('select')
    expect(wrapper.emitted('go-agent')).toEqual([['ai_news']])

    // 点击股票分析名牌 → 跳转 stock
    await plates.find((c) => c.props('text') === '股票分析').vm.$emit('select')
    expect(wrapper.emitted('go-agent')).toEqual([['ai_news'], ['stock']])
  })
})
