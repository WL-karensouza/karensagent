/* ═══════════════════════════════════════════
   fbx2glb —— 资产转换脚本：FBX → GLB（保留骨架动画 + 蒙皮 + 内嵌贴图）
   用项目已有的 three（FBXLoader 读 + GLTFExporter 写），无需 Blender / fbx2gltf 等系统工具
   用法：node scripts/fbx2glb.mjs [input.fbx] [output.glb]
         不传参则默认转 public/models/worker/Seated Idle.fbx → worker_seated.glb
   属一次性/可复用的资产管线工具，非产品运行代码
   ═══════════════════════════════════════════ */
import { readFileSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { FBXLoader } from 'three/examples/jsm/loaders/FBXLoader.js'
import { GLTFExporter } from 'three/examples/jsm/exporters/GLTFExporter.js'
import { Box3, Vector3 } from 'three'

/* node 无浏览器全局；FBXLoader / GLTFExporter 个别路径可能查 self / window，做最小 polyfill */
if (typeof globalThis.self === 'undefined') globalThis.self = globalThis
if (typeof globalThis.window === 'undefined') globalThis.window = globalThis

const here = dirname(fileURLToPath(import.meta.url))
/* 默认输入/输出在脚本内拼好（含空格的输入名不经 shell，免去转义） */
const workerDir = resolve(here, '../public/models/worker')
const inp = process.argv[2] || resolve(workerDir, 'Seated Idle.fbx')
const out = process.argv[3] || resolve(workerDir, 'worker_seated.glb')

const buf = readFileSync(inp)
const arrayBuf = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength)
console.log('[read]', inp, buf.byteLength, 'bytes')

/* 解析 FBX（同步）；内嵌贴图在 node 下若需解码可能在此抛错，捕获后打印以便针对性处理 */
let object
try {
  object = new FBXLoader().parse(arrayBuf, dirname(inp) + '/')
} catch (e) {
  console.error('[parse error]', e && e.message ? e.message : e)
  process.exit(1)
}

/* 诊断：动画列表（确认坐动画在 + 名字，供 AnimationMixer / useAnimations 选用） */
console.log('[animations]', (object.animations || []).map((a) => a.name))
/* 诊断：包围盒（供肉眼对齐 y 偏移 / 朝向参考） */
const box = new Box3().setFromObject(object)
const size = new Vector3()
box.getSize(size)
console.log(
  '[bbox] min', box.min.x.toFixed(3), box.min.y.toFixed(3), box.min.z.toFixed(3),
  '| max', box.max.x.toFixed(3), box.max.y.toFixed(3), box.max.z.toFixed(3),
  '| size', size.x.toFixed(3), size.y.toFixed(3), size.z.toFixed(3),
)
/* 诊断：顶层子节点（看骨架 / 网格结构） */
console.log('[children]', object.children.map((c) => `${c.type}:${c.name}`))

/* 导出 GLB；GLTFExporter 在不同 three 版本可能是 callback 或 Promise，二者兼容、done 防双触发 */
const exporter = new GLTFExporter()
let done = false
const finish = (result) => {
  if (done) return
  done = true
  const outBuf =
    result instanceof ArrayBuffer
      ? Buffer.from(result)
      : Buffer.from(result.buffer, result.byteOffset, result.byteLength)
  writeFileSync(out, outBuf)
  console.log('[wrote]', out, outBuf.byteLength, 'bytes')
}
const fail = (err) => {
  if (done) return
  done = true
  console.error('[export error]', err && err.message ? err.message : err)
  process.exit(1)
}
const ret = exporter.parse(object, finish, fail, { binary: true })
if (ret && typeof ret.then === 'function') ret.then(finish).catch(fail)
