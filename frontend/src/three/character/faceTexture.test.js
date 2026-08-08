// faceTexture.test.js
import { describe, it, expect } from 'vitest'
import { createFaceTexture } from './faceTexture'

describe('createFaceTexture', () => {
  it('返回带 map 属性的纹理与皮肤色', () => {
    const { texture, skinColor } = createFaceTexture({ gender: 'male' })
    expect(texture).toBeTruthy()
    expect(texture.isCanvasTexture).toBe(true)
    expect(skinColor).toMatch(/^#/)
  })

  it('男女性别产生不同纹理实例', () => {
    const a = createFaceTexture({ gender: 'male' })
    const b = createFaceTexture({ gender: 'female' })
    expect(a.texture).not.toBe(b.texture)
  })
})
