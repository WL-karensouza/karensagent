/* ═══════════════════════════════════════════
   faceTexture —— Canvas 程序化五官贴图
   在 canvas 上绘制眼睛/眉毛/嘴/腮红，输出 CanvasTexture
   供头部 LatheGeometry 网格作 map，避免方块式五官
   ═══════════════════════════════════════════ */
import { CanvasTexture, SRGBColorSpace } from 'three'

const SKIN_MALE = '#F2C29B'
const SKIN_FEMALE = '#F6CDB0'

/**
 * 生成面部纹理
 * @param {{ gender: 'male'|'female' }} opts
 * @returns {{ texture: THREE.CanvasTexture, skinColor: string }}
 */
export function createFaceTexture({ gender = 'male' } = {}) {
  const skinColor = gender === 'male' ? SKIN_MALE : SKIN_FEMALE
  const size = 256
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size

  // F1：happy-dom 等无真实 2D 渲染的环境下 getContext('2d') 返回 null，
  // 此时跳过全部绘制，仍返回纯色底 CanvasTexture，保证测试兜底可用。
  const ctx = canvas.getContext('2d')
  if (ctx) {
    // 底色
    ctx.fillStyle = skinColor
    ctx.fillRect(0, 0, size, size)

    // 眼睛（白色巩膜 + 深色虹膜 + 高光）
    const eyeY = 118
    const eyeGap = 74
    ctx.fillStyle = '#ffffff'
    ctx.beginPath()
    ctx.ellipse(size / 2 - eyeGap, eyeY, 17, 12, 0, 0, Math.PI * 2)
    ctx.ellipse(size / 2 + eyeGap, eyeY, 17, 12, 0, 0, Math.PI * 2)
    ctx.fill()
    ctx.fillStyle = '#3A2A20'
    ctx.beginPath()
    ctx.arc(size / 2 - eyeGap, eyeY, 6, 0, Math.PI * 2)
    ctx.arc(size / 2 + eyeGap, eyeY, 6, 0, Math.PI * 2)
    ctx.fill()
    // 高光
    ctx.fillStyle = '#ffffff'
    ctx.beginPath()
    ctx.arc(size / 2 - eyeGap + 2, eyeY - 2, 2, 0, Math.PI * 2)
    ctx.arc(size / 2 + eyeGap + 2, eyeY - 2, 2, 0, Math.PI * 2)
    ctx.fill()

    // 眉毛
    ctx.strokeStyle = '#6B4A2E'
    ctx.lineWidth = 5
    ctx.lineCap = 'round'
    const browY = gender === 'male' ? 88 : 84
    for (const s of [-1, 1]) {
      ctx.beginPath()
      ctx.moveTo(size / 2 + s * (eyeGap - 16), browY)
      ctx.lineTo(size / 2 + s * (eyeGap + 16), browY + (gender === 'male' ? 2 : -2))
      ctx.stroke()
    }

    // 嘴
    ctx.strokeStyle = '#C46A4A'
    ctx.lineWidth = 4
    ctx.beginPath()
    ctx.arc(size / 2, 176, 13, 0.1 * Math.PI, 0.9 * Math.PI)
    ctx.stroke()

    // 腮红（女士更明显）
    ctx.fillStyle = gender === 'female' ? 'rgba(255,140,120,0.35)' : 'rgba(255,160,140,0.2)'
    for (const s of [-1, 1]) {
      ctx.beginPath()
      ctx.ellipse(size / 2 + s * (eyeGap + 26), 150, 12, 8, 0, 0, Math.PI * 2)
      ctx.fill()
    }
  }

  const texture = new CanvasTexture(canvas)
  texture.colorSpace = SRGBColorSpace
  texture.anisotropy = 8
  return { texture, skinColor }
}
