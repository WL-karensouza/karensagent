# 自研骨骼化办公人员实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用纯 three.js 代码自建两个可站立、走动、交流的风格化人物，替换现有外部 FBX 坐姿模型。

**Architecture:** 新增 `frontend/src/three/character/` 目录，内含人物构建器（几何+骨骼+材质）、Canvas 五官贴图、动画 clip、运动状态机。改造 `OfficeWorker.vue` 用自建角色替换 useFBX，`OfficeScene.vue` 挂气泡层与会谈调度。整个系统基于 three.js 0.179 原生动画（SkinnedMesh + AnimationMixer），不依赖外部模型资产。

**Tech Stack:** Vue 3 + TresJS (@tresjs/core ^5.8, @tresjs/cientos ^5.8) + three ^0.179.0 + Vitest。

## Global Constraints

- **技术栈**：仅使用已有的 `three`（^0.179.0）与 `@tresjs/cientos`（^5.8），**不得新增任何 npm 依赖**（编码规范第 8 条）。
- **命名**：JS 变量/函数 camelCase，组件文件 PascalCase（编码规范第 7 条）。
- **风格**：沿用现有 `frontend/src/components/office/` 的注释规范——文件头 `/* ══ ... ══ */` 注释块说明职责（编码规范第 4、5 条）。
- **配色（王磊哥哥拍板）**：男士（AI 前沿工位）**浅蓝色衬衫**、女士（股票工位）**橙色衬衫**。
- **不重构无关代码**：只动办公室人物相关文件，不碰报告/股票功能（编码规范第 9、11 条）。
- **依赖加载守卫**：three 对象一律 `shallowRef`/`markRaw`，绝不能进 Vue 深度 reactive（否则 modelViewMatrix 崩溃）。
- **交接文档**：设计依据见 `docs/superpowers/specs/2026-08-08-office-character-design.md`。

---

### Task 1: 五官贴图生成器 `faceTexture.js`

**Files:**
- Create: `frontend/src/three/character/faceTexture.js`
- Test: `frontend/src/three/character/faceTexture.test.js`

**Interfaces:**
- Consumes: 无（独立工具，纯函数）
- Produces: `createFaceTexture({ gender, skinColor }) → { texture: THREE.CanvasTexture, skinColor: string }` —— gender 为 `'male' | 'female'`；返回的 texture 已设 `colorSpace = SRGBColorSpace`、`anisotropy = 8`，可直接作为头部 Mesh 的 `map`。

- [ ] **Step 1: 写失败测试**

```js
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
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd d:/karensAgent/frontend && npx vitest run src/three/character/faceTexture.test.js`
Expected: FAIL —— `Cannot find module './faceTexture'`

- [ ] **Step 3: 写实现**

```js
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
  const ctx = canvas.getContext('2d')

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

  const texture = new CanvasTexture(canvas)
  texture.colorSpace = SRGBColorSpace
  texture.anisotropy = 8
  return { texture, skinColor }
}
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd d:/karensAgent/frontend && npx vitest run src/three/character/faceTexture.test.js`
Expected: PASS (2 tests)

- [ ] **Step 5: 提交**

```bash
cd d:/karensAgent && git add frontend/src/three/character/
git commit -m "feat(office): 新增人物五官贴图生成器"
```

---

### Task 2: 人物构建器 `buildCharacter.js`

**Files:**
- Create: `frontend/src/three/character/buildCharacter.js`
- Test: `frontend/src/three/character/buildCharacter.test.js`

**Interfaces:**
- Consumes: Task 1 的 `createFaceTexture({ gender })`
- Produces: `buildCharacter({ gender, shirtColor }) → { group, skeleton, mixer }`
  - `group`: `THREE.Group`，已含完整人形（SkinnedMesh 各部位 + 骨骼），放置到场景 `(0,0,0)` 站立，脚踩 y=0，根骨骼名 `Hips`
  - `skeleton.bones`: 骨骼数组，含 `Hips/Spine/Chest/Neck/Head`、`LeftUpperArm/LeftLowerArm/LeftHand`（右同）、`LeftUpperLeg/LeftLowerLeg/LeftFoot`（右同）
  - `mixer`: `THREE.AnimationMixer`，绑定到 `group`，供动画系统使用

- [ ] **Step 1: 写失败测试**

```js
// buildCharacter.test.js
import { describe, it, expect } from 'vitest'
import { buildCharacter } from './buildCharacter'

describe('buildCharacter', () => {
  it('返回带骨架与混音器的角色分组', () => {
    const { group, skeleton, mixer } = buildCharacter({ gender: 'male', shirtColor: '#9CC7E8' })
    expect(group).toBeTruthy()
    expect(skeleton).toBeTruthy()
    expect(mixer).toBeTruthy()
    expect(group.children.length).toBeGreaterThan(0)
  })

  it('骨骼包含关键命名节点', () => {
    const { skeleton } = buildCharacter({ gender: 'female', shirtColor: '#D97706' })
    const names = skeleton.bones.map((b) => b.name)
    for (const key of ['Hips', 'Spine', 'Chest', 'Neck', 'Head',
      'LeftUpperArm', 'LeftLowerArm', 'LeftHand',
      'LeftUpperLeg', 'LeftLowerLeg', 'LeftFoot']) {
      expect(names).toContain(key)
    }
  })

  it('脚底对齐 y=0', () => {
    const { group } = buildCharacter({ gender: 'male', shirtColor: '#9CC7E8' })
    const box = new THREE.Box3().setFromObject(group)
    expect(box.min.y).toBeCloseTo(0, 1)
  })
})
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd d:/karensAgent/frontend && npx vitest run src/three/character/buildCharacter.test.js`
Expected: FAIL —— 模块不存在 / THREE 未定义

- [ ] **Step 3: 写实现**（核心：Lathe 头 + 胶囊四肢 + 骨骼装配 + SkinnedMesh）

```js
/* ═══════════════════════════════════════════
   buildCharacter —— 自研骨骼化人物构建器
   风格化精致人物：Lathe 头 + 胶囊四肢 + 球关节 + 骨骼绑定
   输出 { group, skeleton, mixer }，供状态机与动画系统驱动
   ═══════════════════════════════════════════ */
import {
  Group, Bone, Skeleton, SkinnedMesh, MeshStandardMaterial,
  LatheGeometry, SphereGeometry, CapsuleGeometry, Vector2, Vector3,
  AnimationMixer, Color,
} from 'three'
import { createFaceTexture } from './faceTexture'

/* 人体关节位置（米，以脚底为 y=0） */
const H = {
  hipY: 0.95,        // 髋
  spineY: 1.15,      // 脊柱
  chestY: 1.32,      // 胸
  neckY: 1.52,       // 颈
  headY: 1.62,       // 头
  shoulderY: 1.38,   // 肩
  elbowY: 1.16,      // 肘
  handY: 0.95,       // 手
  kneeY: 0.48,       // 膝
  ankleY: 0.08,      // 踝
}

/* 创建胶囊网格，可绑定骨骼 */
function makePart(geo, mat, bone, pos, cast = true) {
  const mesh = new SkinnedMesh(geo, mat)
  mesh.position.copy(pos)
  mesh.castShadow = cast
  mesh.receiveShadow = true
  mesh.add(bone)
  mesh.bind(new Skeleton([bone]))
  return mesh
}

/**
 * 构建人物
 * @param {{ gender: 'male'|'female', shirtColor: string }} opts
 * @returns {{ group: THREE.Group, skeleton: THREE.Skeleton, mixer: THREE.AnimationMixer }}
 */
export function buildCharacter({ gender = 'male', shirtColor = '#9CC7E8' } = {}) {
  const group = new Group()
  const { texture: faceTex, skinColor } = createFaceTexture({ gender })

  const skinMat = new MeshStandardMaterial({ map: faceTex, roughness: 0.55 })
  const shirtMat = new MeshStandardMaterial({ color: new Color(shirtColor), roughness: 0.9 })
  const pantsMat = new MeshStandardMaterial({ color: '#3A3E45', roughness: 0.85 })
  const hairMat = new MeshStandardMaterial({ color: '#2B211A', roughness: 0.4 })

  // ── 骨骼层级 ──
  const bones = {}
  const names = [
    'Hips', 'Spine', 'Chest', 'Neck', 'Head',
    'LeftClavicle', 'LeftUpperArm', 'LeftLowerArm', 'LeftHand',
    'RightClavicle', 'RightUpperArm', 'RightLowerArm', 'RightHand',
    'LeftUpperLeg', 'LeftLowerLeg', 'LeftFoot',
    'RightUpperLeg', 'RightLowerLeg', 'RightFoot',
  ]
  for (const n of names) {
    bones[n] = new Bone()
    bones[n].name = n
  }

  const pos = (name) => bones[name].position
  // 脊柱
  pos('Hips').set(0, H.hipY, 0)
  pos('Spine').set(0, H.spineY - H.hipY, 0)
  pos('Chest').set(0, H.chestY - H.spineY, 0)
  pos('Neck').set(0, H.neckY - H.chestY, 0)
  pos('Head').set(0, H.headY - H.neckY, 0)

  // 手臂（肩宽随性别）
  const shoulder = gender === 'male' ? 0.33 : 0.28
  const armLen = H.shoulderY - H.handY // 大臂+小臂总长
  pos('LeftClavicle').set(-shoulder, 0, 0)
  pos('LeftUpperArm').set(0, -armLen * 0.48, 0)
  pos('LeftLowerArm').set(0, -armLen * 0.52, 0)
  pos('LeftHand').set(0, -0.08, 0)
  pos('RightClavicle').set(shoulder, 0, 0)
  pos('RightUpperArm').set(0, -armLen * 0.48, 0)
  pos('RightLowerArm').set(0, -armLen * 0.52, 0)
  pos('RightHand').set(0, -0.08, 0)

  // 腿
  const legSpread = gender === 'male' ? 0.12 : 0.10
  pos('LeftUpperLeg').set(-legSpread, -0.4, 0)
  pos('LeftLowerLeg').set(0, -0.42, 0)
  pos('LeftFoot').set(0, -0.06, 0.05)
  pos('RightUpperLeg').set(legSpread, -0.4, 0)
  pos('RightLowerLeg').set(0, -0.42, 0)
  pos('RightFoot').set(0, -0.06, 0.05)

  // 层级挂接
  const chain = [
    ['Hips', 'Spine'], ['Spine', 'Chest'], ['Chest', 'Neck'], ['Neck', 'Head'],
    ['Chest', 'LeftClavicle'], ['LeftClavicle', 'LeftUpperArm'],
    ['LeftUpperArm', 'LeftLowerArm'], ['LeftLowerArm', 'LeftHand'],
    ['Chest', 'RightClavicle'], ['RightClavicle', 'RightUpperArm'],
    ['RightUpperArm', 'RightLowerArm'], ['RightLowerArm', 'RightHand'],
    ['Hips', 'LeftUpperLeg'], ['LeftUpperLeg', 'LeftLowerLeg'], ['LeftLowerLeg', 'LeftFoot'],
    ['Hips', 'RightUpperLeg'], ['RightUpperLeg', 'RightLowerLeg'], ['RightLowerLeg', 'RightFoot'],
  ]
  for (const [p, c] of chain) bones[p].add(bones[c])

  const root = bones.Hips
  const skeleton = new Skeleton(Object.values(bones))

  // ── 网格：绑定骨骼 ──
  // 头（Lathe 平滑曲面 + 五官贴图）
  const headProfile = [
    new Vector2(0, 0), new Vector2(0.13, 0.02), new Vector2(0.155, 0.08),
    new Vector2(0.15, 0.2), new Vector2(0.12, 0.28),
  ]
  const headGeo = new LatheGeometry(headProfile, 24)
  headGeo.computeVertexNormals()
  const headMesh = makePart(headGeo, skinMat, bones.Head, new Vector3(0, 0.09, 0))

  // 躯干（锥形，宽肩收腰）
  const torsoGeo = new LatheGeometry([
    new Vector2(0, 0), new Vector2(0.22, 0), new Vector2(0.26, 0.08),
    new Vector2(0.28, 0.22), new Vector2(0.24, 0.36), new Vector2(0.2, 0.44),
  ], 24)
  torsoGeo.computeVertexNormals()
  const torsoMesh = makePart(torsoGeo, shirtMat, bones.Spine, new Vector3(0, -0.02, 0))

  // 手臂：肩球 + 大臂/小臂胶囊
  const shoulderGeo = new SphereGeometry(0.09, 16, 16)
  for (const s of [-1, 1]) {
    const upName = s < 0 ? 'LeftUpperArm' : 'RightUpperArm'
    const lowName = s < 0 ? 'LeftLowerArm' : 'RightLowerArm'
    const handName = s < 0 ? 'LeftHand' : 'RightHand'
    const sMesh = makePart(shoulderGeo, shirtMat, bones[upName], new Vector3(0, 0, 0))
    const upArm = makePart(new CapsuleGeometry(0.055, 0.26, 6, 16), shirtMat, bones[upName], new Vector3(0, -0.12, 0))
    const lowArm = makePart(new CapsuleGeometry(0.045, 0.26, 6, 16), shirtMat, bones[lowName], new Vector3(0, -0.12, 0))
    const hand = makePart(new SphereGeometry(0.05, 12, 12), skinMat, bones[handName], new Vector3(0, -0.04, 0))
    group.add(sMesh, upArm, lowArm, hand)
  }

  // 腿：大腿/小腿胶囊 + 圆脚
  for (const s of [-1, 1]) {
    const upName = s < 0 ? 'LeftUpperLeg' : 'RightUpperLeg'
    const lowName = s < 0 ? 'LeftLowerLeg' : 'RightLowerLeg'
    const footName = s < 0 ? 'LeftFoot' : 'RightFoot'
    const upLeg = makePart(new CapsuleGeometry(0.08, 0.34, 6, 16), pantsMat, bones[upName], new Vector3(0, -0.17, 0))
    const lowLeg = makePart(new CapsuleGeometry(0.065, 0.34, 6, 16), pantsMat, bones[lowName], new Vector3(0, -0.17, 0))
    const foot = makePart(new SphereGeometry(0.065, 12, 12), pantsMat, bones[footName], new Vector3(0, -0.03, 0.02))
    group.add(upLeg, lowLeg, foot)
  }

  // 头发（男士短发贴片 / 女士长发垂片）
  const hairGeo = gender === 'male'
    ? new LatheGeometry([new Vector2(0.1, 0), new Vector2(0.14, 0.05), new Vector2(0.14, 0.12), new Vector2(0.12, 0.16)], 24)
    : new LatheGeometry([new Vector2(0.11, 0), new Vector2(0.15, 0.06), new Vector2(0.15, 0.2), new Vector2(0.13, 0.3)], 24)
  hairGeo.computeVertexNormals()
  const hairMesh = makePart(hairGeo, hairMat, bones.Head, new Vector3(0, 0.09, -0.005))

  group.add(headMesh, torsoMesh, hairMesh, root)

  const mixer = new AnimationMixer(group)
  return { group, skeleton, mixer }
}
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd d:/karensAgent/frontend && npx vitest run src/three/character/buildCharacter.test.js`
Expected: PASS (3 tests)

- [ ] **Step 5: 提交**

```bash
cd d:/karensAgent && git add frontend/src/three/character/
git commit -m "feat(office): 新增骨骼化人物构建器"
```

---

### Task 3: 动画 clip 定义 `characterAnimations.js`

**Files:**
- Create: `frontend/src/three/character/characterAnimations.js`
- Test: `frontend/src/three/character/characterAnimations.test.js`

**Interfaces:**
- Consumes: 无（独立纯函数，骨骼名约定见 Task 2）
- Produces:
  - `createAnimations() → { idleStand, walk, sit, standUp, sitIdle, talk, wave, reactClick }`
  - 每个值均为 `THREE.AnimationClip`，命名遵循：
    - 位移类（walk）在 **Hips** 上含 position track（`.position`）
    - 姿态类在骨骼上含 `.rotation` track（弧度），使用 `KEYFRAME_TRACK_TYPE_QUATERNION`（三轴旋转）或旋转欧拉
  - 动画时长为秒；循环类 `loop = true`，一次性类 `loop = false`

- [ ] **Step 1: 写失败测试**

```js
// characterAnimations.test.js
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
})
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd d:/karensAgent/frontend && npx vitest run src/three/character/characterAnimations.test.js`
Expected: FAIL

- [ ] **Step 3: 写实现**（用 Quaternion 关键帧插值，避免万向锁）

```js
/* ═══════════════════════════════════════════
   characterAnimations —— 手写人物动画 clip
   姿态类：骨骼 rotation 关键帧（四元数，无万向锁）
   位移类：Hips.position 关键帧（如 walk 前进）
   循环类 loop=true；一次性类 loop=false
   ═══════════════════════════════════════════ */
import {
  AnimationClip, Quaternion, Vector3, Euler, VectorKeyframeTrack, QuaternionKeyframeTrack,
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
    rotTrack('Hips', [0, 1.2], [q(0, 0, 0), q(0, 0, 0)]),
    rotTrack('Spine', [0, 0.3, 1.2], [q(0, 0, 0), q(0.2, 0, 0), q(0, 0, 0)]),
    rotTrack('RightUpperArm', [0, 0.2, 0.6, 1.0, 1.2], [q(0, 0, 0), q(-2.4, 0, -0.3), q(-2.4, 0, 0.3), q(-2.4, 0, -0.3), q(0, 0, 0)]),
  ])

  return { idleStand, walk, sit, standUp, sitIdle, talk, wave, reactClick }
}
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd d:/karensAgent/frontend && npx vitest run src/three/character/characterAnimations.test.js`
Expected: PASS (3 tests)

- [ ] **Step 5: 提交**

```bash
cd d:/karensAgent && git add frontend/src/three/character/
git commit -m "feat(office): 新增人物动画 clip 定义"
```

---

### Task 4: 运动状态机 `useCharacterMotion.js`

**Files:**
- Create: `frontend/src/three/character/useCharacterMotion.js`
- Test: `frontend/src/three/character/useCharacterMotion.test.js`

**Interfaces:**
- Consumes:
  - Task 2 的 `buildCharacter()` 返回 `{ group, skeleton, mixer }`
  - Task 3 的 `createAnimations()` 返回的 clip 集合
- Produces:
  - `createMotionController({ group, skeleton, mixer, animations, waypoints, speed, onReachWaypoint }) → controller`
  - `controller` 方法：
    - `update(delta, time)` —— 每帧调用，推进状态机（内部处理走/停/转向）
    - `walkTo(x, z)` —— 设置目标点，进入 WALK 状态（自动转向 + 匀速移动）
    - `setState(state)` —— 手动切换姿态（`'idle' | 'walk' | 'sit' | 'standUp' | 'talk'`）
    - `faceToward(x, z)` —— 原地平滑转向目标（quaternion slerp）
    - `isMoving()` —— 是否在走动
  - 状态机状态：`'IDLE' | 'WALK' | 'SIT' | 'STAND_UP' | 'TALK'`

- [ ] **Step 1: 写失败测试**

```js
// useCharacterMotion.test.js
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
})
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd d:/karensAgent/frontend && npx vitest run src/three/character/useCharacterMotion.test.js`
Expected: FAIL

- [ ] **Step 3: 写实现**（移动/转向 + 状态机核心）

```js
/* ═══════════════════════════════════════════
   useCharacterMotion —— 人物运动状态机
   状态：IDLE / WALK / SIT / STAND_UP / TALK
   移动：直线前进 + 平滑转向（quaternion slerp）
   姿态：通过 mixer 播放对应 clip
   ═══════════════════════════════════════════ */
import { Quaternion, Vector3 } from 'three'

const EPS = 1e-4

export function createMotionController({ group, mixer, animations, waypoints = [], speed = 1, onReachWaypoint = null }) {
  let state = 'IDLE'
  let target = null           // { x, z }
  let prevQuat = new Quaternion()
  let action = null
  const forward = new Vector3(0, 0, 1)

  /* 播放某 clip，可选混合 */
  function playClip(name, fadeIn = 0.2) {
    if (action) action.fadeOut(0.1)
    const next = mixer.clipAction(animations[name])
    next.reset().fadeIn(fadeIn).play()
    action = next
  }

  function setState(next) {
    if (state === next) return
    state = next
    switch (state) {
      case 'idle': playClip('idleStand'); break
      case 'walk': playClip('walk'); break
      case 'sit': playClip('sit'); break
      case 'standUp': playClip('standUp'); break
      case 'talk': playClip('talk'); break
    }
  }

  function walkTo(x, z) {
    target = { x, z }
    setState('walk')
  }

  function faceToward(x, z) {
    const dx = x - group.position.x
    const dz = z - group.position.z
    if (Math.hypot(dx, dz) < EPS) return
    const q = new Quaternion().setFromUnitVectors(forward, new Vector3(dx, 0, dz).normalize())
    group.quaternion.copy(q)
  }

  function isMoving() {
    return state === 'WALK' || target != null
  }

  function update(delta) {
    mixer.update(delta)

    if (target) {
      const dx = target.x - group.position.x
      const dz = target.z - group.position.z
      const dist = Math.hypot(dx, dz)
      if (dist < EPS) {
        target = null
        setState('idle')
        onReachWaypoint?.()
        return
      }
      // 平滑转向
      faceToward(target.x, target.z)
      // 前进
      group.position.x += (dx / dist) * speed * delta
      group.position.z += (dz / dist) * speed * delta
    }
  }

  return { update, walkTo, setState, faceToward, isMoving, get state() { return state } }
}
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd d:/karensAgent/frontend && npx vitest run src/three/character/useCharacterMotion.test.js`
Expected: PASS (3 tests)

- [ ] **Step 5: 提交**

```bash
cd d:/karensAgent && git add frontend/src/three/character/
git commit -m "feat(office): 新增人物运动状态机"
```

---

### Task 5: 对话气泡组件 `CharacterBubble.vue`

**Files:**
- Create: `frontend/src/three/character/CharacterBubble.vue`
- Test: `frontend/src/three/character/CharacterBubble.test.js`

**Interfaces:**
- Consumes: Vue 3 标准 props；`THREE.Vector3` 世界坐标
- Produces: 通过 `@tresjs/core` 的 `useTres()` 提供 `show(text)` 方法（在组件暴露 `defineExpose({ show })`），气泡在给定世界坐标上方显示，数秒自动消失

- [ ] **Step 1: 写失败测试**

```js
// CharacterBubble.test.js
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import CharacterBubble from './CharacterBubble.vue'

describe('CharacterBubble', () => {
  it('渲染容器', () => {
    const wrapper = mount(CharacterBubble, { props: { target: { x: 0, y: 0, z: 0 } } })
    expect(wrapper.exists()).toBe(true)
  })

  it('调用 show 后出现文本气泡', async () => {
    const wrapper = mount(CharacterBubble, { props: { target: { x: 0, y: 0, z: 0 } } })
    await wrapper.vm.show('你好')
    const text = wrapper.text()
    expect(text).toContain('你好')
  })
})
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd d:/karensAgent/frontend && npx vitest run src/three/character/CharacterBubble.test.js`
Expected: FAIL

- [ ] **Step 3: 写实现**（世界坐标→屏幕投影 + 气泡 div）

```vue
<script setup>
/* ═══════════════════════════════════════════
   CharacterBubble —— 人物头顶对话气泡
   输入目标世界坐标，渲染循环投影到屏幕定位 div
   show(text) 显示台词，DURATION 秒后自动淡出
   ═══════════════════════════════════════════ */
import { ref, onMounted, onUnmounted } from 'vue'
import { useTres, useLoop } from '@tresjs/core'
import { Vector3 } from 'three'

const props = defineProps({
  target: { type: Object, default: () => ({ x: 0, y: 2, z: 0 }) }, // 世界坐标（头顶上方）
})

const DURATION = 3000
const visible = ref(false)
const text = ref('')
const style = ref({ left: '50%', top: '50%' })
let hideTimer = null
let worldPos = new Vector3(props.target.x, props.target.y, props.target.z)

const { camera } = useTres()
const { onRender } = useLoop()

onRender(() => {
  if (!visible.value) return
  const cam = camera.value?.__tres?.object ?? camera.value
  if (!cam) return
  // 世界→屏幕投影
  const v = worldPos.clone().project(cam)
  if (v.z < 1) {
    style.value = {
      left: `${(v.x * 0.5 + 0.5) * 100}%`,
      top: `${(-v.y * 0.5 + 0.5) * 100}%`,
    }
  }
})

function show(msg) {
  text.value = msg
  visible.value = true
  clearTimeout(hideTimer)
  hideTimer = setTimeout(() => { visible.value = false }, DURATION)
}

defineExpose({ show })

onUnmounted(() => clearTimeout(hideTimer))
</script>

<template>
  <div class="character-bubble-layer">
    <transition name="bubble">
      <div v-if="visible" class="character-bubble" :style="style">
        {{ text }}
        <span class="bubble-arrow" />
      </div>
    </transition>
  </div>
</template>

<style scoped>
/* ══ 对话气泡浮层 ══
   绝对定位覆盖场景；气泡投影定位；白底圆角+箭头+浅色描边 */
.character-bubble-layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
}
.character-bubble {
  position: absolute;
  transform: translate(-50%, -100%);
  padding: 6px 14px;
  background: rgba(255, 255, 255, 0.95);
  color: var(--text-secondary, #444);
  font-size: 0.85rem;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.12);
  border: 1px solid rgba(0, 0, 0, 0.06);
}
.bubble-arrow {
  position: absolute;
  left: 50%;
  bottom: -6px;
  transform: translateX(-50%);
  width: 12px;
  height: 12px;
  background: inherit;
  border-right: 1px solid rgba(0, 0, 0, 0.06);
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  transform: translateX(-50%) rotate(45deg);
}
.bubble-enter-active, .bubble-leave-active { transition: opacity 0.2s ease; }
.bubble-enter-from, .bubble-leave-to { opacity: 0; }
</style>
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd d:/karensAgent/frontend && npx vitest run src/three/character/CharacterBubble.test.js`
Expected: PASS (2 tests)

- [ ] **Step 5: 提交**

```bash
cd d:/karensAgent && git add frontend/src/three/character/
git commit -m "feat(office): 新增人物对话气泡组件"
```

---

### Task 6: 改造 `OfficeWorker.vue` 用自建角色

**Files:**
- Modify: `frontend/src/components/office/OfficeWorker.vue`
- Test: `frontend/src/components/office/OfficeWorker.test.js` (新建)

**Interfaces:**
- Consumes: Task 2 `buildCharacter`、Task 3 `createAnimations`、Task 4 `createMotionController`
- Produces: 与 OfficeScene 的既有接口不变 —— props `position`/`workerId`，emits `select`；但内部改用自建角色替代 useFBX；新增 emit `bubble`（`(text) => void`，供 OfficeScene 气泡层调用）

- [ ] **Step 1: 写失败测试**（验证 props 接口不变 + 自建角色挂载）

```js
// OfficeWorker.test.js
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import OfficeWorker from './OfficeWorker.vue'
import { vi } from 'vitest'

// 需要 stub 掉 three 相关（happy-dom 无 WebGL）
vi.mock('@tresjs/core', () => ({
  useTres: () => ({ camera: { value: null } }),
  useLoop: () => ({ onRender: vi.fn(), onBeforeRender: vi.fn() }),
}))
vi.mock('@tresjs/cientos', () => ({ useFBX: () => ({ state: { value: null }, error: { value: null } }) }))

describe('OfficeWorker', () => {
  it('接受 position 与 workerId props', () => {
    const wrapper = mount(OfficeWorker, {
      props: { position: [-3, 0, -2], workerId: 'ai_news' },
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('点击触发 select 事件', async () => {
    const wrapper = mount(OfficeWorker, {
      props: { position: [3, 0, -2], workerId: 'stock' },
    })
    wrapper.trigger('click')
    expect(wrapper.emitted('select')).toBeTruthy()
  })
})
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd d:/karensAgent/frontend && npx vitest run src/components/office/OfficeWorker.test.js`
Expected: FAIL —— 现有测试文件不存在

- [ ] **Step 3: 改造实现**（完整替换脚本体，删除 useFBX/诊断面板/对齐逻辑）

```vue
<script setup>
/* ═══════════════════════════════════════════
   OfficeWorker —— 工作人员（自研骨骼化人物）
   用 buildCharacter 构建风格化人物 + 状态机驱动
   替代原 useFBX 加载 Mixamo 坐姿模型
   交互：点击上抛 select；悬停挥手+看镜头+手形光标
   ═══════════════════════════════════════════ */
import { ref, shallowRef, watch, onMounted, onUnmounted } from 'vue'
import { useLoop } from '@tresjs/core'
import { buildCharacter } from '../../three/character/buildCharacter'
import { createAnimations } from '../../three/character/characterAnimations'
import { createMotionController } from '../../three/character/useCharacterMotion'

const props = defineProps({
  position: { type: Array, default: () => [0, 0, 0] },
  workerId: { type: String, default: 'ai_news' },
})
const emit = defineEmits(['select', 'bubble'])

/* 主题色：男士浅蓝 / 女士橙色（王磊哥哥拍板） */
const GENDER = props.workerId === 'stock' ? 'female' : 'male'
const SHIRT = props.workerId === 'stock' ? '#D97706' : '#9CC7E8'

/* 自建角色 */
const char = shallowRef(null) // 角色 group（禁深代理）
let mixer = null
let motion = null
const { onRender } = useLoop()

/* 构建角色（在 useLoop 就绪后） */
function ensureBuilt() {
  if (char.value) return
  const built = buildCharacter({ gender: GENDER, shirtColor: SHIRT })
  built.group.position.set(props.position[0], 0, props.position[2])
  mixer = built.mixer
  const animations = createAnimations()
  motion = createMotionController({
    group: built.group,
    mixer,
    animations,
    speed: 0.8,
  })
  // 先播放 idleStand
  mixer.clipAction(animations.idleStand).reset().play()
  char.value = built.group
}

/* 每帧推进状态机 */
onRender(({ delta }) => {
  if (mixer && motion) motion.update(delta)
})

/* 交互 */
const hovered = ref(false)
function onOver() {
  hovered.value = true
  document.body.style.cursor = 'pointer'
  // 悬停：挥手 + 看镜头
  if (motion) motion.setState('talk')
}
function onOut() {
  hovered.value = false
  document.body.style.cursor = 'auto'
  if (motion) motion.setState('idle')
}
function onClick() {
  // 播打招呼动画后跳转
  if (motion) motion.setState('standUp')
  setTimeout(() => emit('select', props.workerId), 600)
}

/* 暴露给 OfficeScene：会谈调度驱动工人走向目标 */
function walkTo(x, z) {
  if (motion) motion.walkTo(x, z)
}
defineExpose({ walkTo })
</script>

<template>
  <TresGroup
    :position="position"
    @click="onClick"
    @pointer-over="onOver"
    @pointer-out="onOut"
  >
    <primitive v-if="char" :object="char" />
  </TresGroup>
</template>
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd d:/karensAgent/frontend && npx vitest run src/components/office/OfficeWorker.test.js`
Expected: PASS (2 tests)

- [ ] **Step 5: 提交**

```bash
cd d:/karensAgent && git add frontend/src/components/office/OfficeWorker.vue frontend/src/components/office/OfficeWorker.test.js
git commit -m "feat(office): OfficeWorker 改用自研骨骼化人物"
```

---

### Task 7: 会谈调度与气泡集成（`OfficeScene.vue`）

**Files:**
- Modify: `frontend/src/components/office/OfficeScene.vue`
- Test: `frontend/src/components/office/OfficeScene.test.js` (新建)

**Interfaces:**
- Consumes: Task 5 `CharacterBubble.vue`、Task 4 运动控制器的 `walkTo`/`faceToward`
- Produces: 对 OfficeHome 的既有接口不变（`@ready` / `@go-agent`）；新增内部会谈调度逻辑

- [ ] **Step 1: 写失败测试**（场景组合不变）

```js
// OfficeScene.test.js
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import OfficeScene from './OfficeScene.vue'
import { vi } from 'vitest'

vi.mock('@tresjs/core', () => ({
  TresCanvas: { inheritAttrs: false, setup: () => () => {} },
  useTres: () => ({ camera: { value: null } }),
  useLoop: () => ({ onRender: vi.fn() }),
}))
vi.mock('@tresjs/cientos', () => ({ OrbitControls: { inheritAttrs: false, setup: () => () => {} } }))

describe('OfficeScene', () => {
  it('渲染两个工位', () => {
    const wrapper = mount(OfficeScene)
    expect(wrapper.text()).toContain('AI 前沿')
    expect(wrapper.text()).toContain('股票分析')
  })
})
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd d:/karensAgent/frontend && npx vitest run src/components/office/OfficeScene.test.js`
Expected: FAIL

- [ ] **Step 3: 改造实现**（挂气泡层 + 会谈调度）

```vue
<script setup>
/* ═══════════════════════════════════════════
   OfficeScene —— 3D 场景组合根组件
   组合房间 / 装饰 / 两个工位 / 大屏 / 名牌
   新增：会谈调度 + 对话气泡层
   ═══════════════════════════════════════════ */
import { ref, onMounted, onUnmounted } from 'vue'
import { TresCanvas } from '@tresjs/core'
import { OrbitControls } from '@tresjs/cientos'
import OfficeRoom from './OfficeRoom.vue'
import OfficeDesk from './OfficeDesk.vue'
import OfficeWorker from './OfficeWorker.vue'
import OfficeNameplate from './OfficeNameplate.vue'
import OfficeWallScreen from './OfficeWallScreen.vue'
import OfficeDecorations from './OfficeDecorations.vue'
import OfficeCameraClamp from './OfficeCameraClamp.vue'
import CharacterBubble from '../../three/character/CharacterBubble.vue'

const emit = defineEmits(['go-agent', 'ready'])
const bubbleRef = ref(null)

/* 台词库（随机轮换） */
const LINES = [
  '今天的大盘数据有点意思，你看看？',
  '我刚跑了最新的策略回测，收益不错！',
  '这个新闻热点值得追踪，帮我盯着点。',
  '午后那波行情你看到了吗？',
  '我整理了一份周报，晚点发你。',
]

/* 会谈调度：启动后随机触发两人走向中央 → 轮流气泡对话 */
let talkTimer = null
function startMeeting() {
  talkTimer = setTimeout(() => {
    // 两人走向中央会谈区
    document.dispatchEvent(new CustomEvent('worker-go', { detail: { id: 'ai_news', x: 0, z: -0.5 } }))
    document.dispatchEvent(new CustomEvent('worker-go', { detail: { id: 'stock', x: 1.2, z: -0.5 } }))
    // 轮流冒泡
    const lines = [...LINES]
    let i = 0
    const iv = setInterval(() => {
      const line = lines[i % lines.length]
      const speaker = i % 2 === 0 ? 'ai_news' : 'stock'
      bubbleRef.value?.show(line)
      i++
      if (i >= 3) { clearInterval(iv); scheduleNext() }
    }, 2000)
  }, 4000)
}
function scheduleNext() {
  talkTimer = setTimeout(startMeeting, 20000 + Math.random() * 15000)
}

onMounted(() => {
  document.addEventListener('worker-go', onWorkerGo)
  startMeeting()
})
onUnmounted(() => {
  clearTimeout(talkTimer)
  document.removeEventListener('worker-go', onWorkerGo)
})

function onWorkerGo(e) {
  // 通过组件方法驱动对应工人走向目标（Task 6 实现）
  const el = workers[e.detail.id]
  el?.walkTo(e.detail.x, e.detail.z)
}
const workers = {}
function onSceneReady() { emit('ready') }
function onWorkerClick(id) { emit('go-agent', id) }
</script>

<template>
  <TresCanvas
    shadows
    antialias
    clear-color="#ECE8E0"
    @ready="onSceneReady"
  >
    <TresPerspectiveCamera :position="[0, 4.3, 4.3]" :fov="60" />
    <OrbitControls
      :enableDamping="true"
      :enablePan="false"
      :minDistance="2"
      :target="[0, 1.1, -1.6]"
    />

    <OfficeRoom />
    <OfficeDecorations />

    <OfficeDesk :position="[-3, 0, -2]" theme="ai_news" />
    <OfficeWorker ref="ai_news" worker-id="ai_news" :position="[-3, 0, -2]" @select="onWorkerClick" />
    <OfficeNameplate :position="[-3, 0.02, -0.6]" text="AI 前沿" />

    <OfficeDesk :position="[3, 0, -2]" theme="stock" />
    <OfficeWorker ref="stock" worker-id="stock" :position="[3, 0, -2]" @select="onWorkerClick" />
    <OfficeNameplate :position="[3, 0.02, -0.6]" text="股票分析" />

    <OfficeWallScreen :position="[0, 2.2, -4.8]" />
    <OfficeCameraClamp />

    <!-- 对话气泡层（世界坐标投影） -->
    <CharacterBubble ref="bubbleRef" />
  </TresCanvas>
</template>
```

> ⚠️ 实现注意：`workers` 引用通过 `ref="ai_news"`/`ref="stock"` 收集，需要在模板渲染后把组件实例的 `walkTo` 暴露出来（组件 `defineExpose({ walkTo })`，由 Task 6 补充）。`onWorkerGo` 通过事件分发解耦。

- [ ] **Step 4: 运行测试验证通过**

Run: `cd d:/karensAgent/frontend && npx vitest run src/components/office/OfficeScene.test.js`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
cd d:/karensAgent && git add frontend/src/components/office/OfficeScene.vue frontend/src/components/office/OfficeScene.test.js
git commit -m "feat(office): 场景接入会谈调度与对话气泡"
```

---

### Task 8: 删除旧 FBX 依赖 + 端到端验证

**Files:**
- Delete: `frontend/public/models/worker/Seated Idle.fbx`
- Modify: `frontend/public/models/README.md`（更新资源说明）
- Verify: 全量测试 + 构建 + 手动浏览器验证

**Interfaces:**
- Consumes: 全部前述任务
- Produces: 干净的资源目录 + 验证通过的完整功能

- [ ] **Step 1: 全量测试**

Run: `cd d:/karensAgent/frontend && npx vitest run`
Expected: 全部 PASS（含 5 个新增单测 + 现有测试）

- [ ] **Step 2: 删除旧 FBX 并更新 README**

```bash
cd d:/karensAgent && git rm "frontend/public/models/worker/Seated Idle.fbx"
```

更新 `frontend/public/models/README.md`：移除 worker FBX 说明，注明"人物已改为纯代码构建，无外部人物模型"。

- [ ] **Step 3: 生产构建**

Run: `cd d:/karensAgent/frontend && npm run build`
Expected: 构建成功，无 import 错误、无未引用模块警告

- [ ] **Step 4: 手动浏览器验证**

Run: `cd d:/karensAgent/frontend && npm run dev`，打开首页 3D 办公室，逐项确认：
- [ ] 两个风格化人物（男浅蓝/女橙色）站立在工位前
- [ ] 数秒后两人走向中央，面对面交谈，头顶轮流冒气泡
- [ ] 悬停人物：看镜头 + 挥手 + 手形光标
- [ ] 点击人物：打招呼后跳转对应工位页
- [ ] 人物走动自然不穿模，可缩放/旋转视角

- [ ] **Step 5: 提交**

```bash
cd d:/karensAgent && git add -A
git commit -m "refactor(office): 移除旧 FBX 人物模型，纯代码人物上线"
```
