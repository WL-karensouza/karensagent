/* ═══════════════════════════════════════════
   buildCharacter —— 自研骨骼化人物构建器
   风格化精致人物：Lathe 头 + 胶囊四肢 + 球关节 + 骨骼绑定
   输出 { group, skeleton, mixer }，供状态机与动画系统驱动
   ═══════════════════════════════════════════ */
import {
  Group, Bone, Skeleton, SkinnedMesh, MeshStandardMaterial,
  LatheGeometry, SphereGeometry, CapsuleGeometry, Vector2, Vector3,
  AnimationMixer, Color, BufferAttribute,
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

/* 创建胶囊网格：网格 add 到 group，用独立 Skeleton 绑定到对应骨骼
   ⚠️ 绝不能 mesh.add(bone) —— 那会把骨骼从 Hips 链摘走，动画失效（F2 修复）
   独立 Skeleton 仅含 1 根骨骼（索引 0），故 skinIndex 全 0、skinWeight=[1,0,0,0]，
   否则 SkinnedMesh.computeBoundingBox / GPU 蒙皮在缺 skin attribute 时崩溃 */
function makePart(geo, mat, bone, pos, cast = true) {
  const mesh = new SkinnedMesh(geo, mat)
  mesh.position.copy(pos)
  mesh.castShadow = cast
  mesh.receiveShadow = true
  // 蒙皮必需属性：每个顶点绑定到该网格唯一的骨骼（索引 0，权重 1）
  const count = geo.attributes.position.count
  const skinIndex = new Float32Array(count * 4)
  const skinWeight = new Float32Array(count * 4)
  for (let i = 0; i < count; i++) skinWeight[i * 4] = 1
  geo.setAttribute('skinIndex', new BufferAttribute(skinIndex, 4))
  geo.setAttribute('skinWeight', new BufferAttribute(skinWeight, 4))
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
  // ⚠️ 小腿胶囊偏移 +0.15：LeftLowerLeg 骨骼在世界 y≈0.13（脚踝处），胶囊居中在膝盖(0.48)与脚踝(0.08)之间，
  //   中心 world y≈0.28、半高 0.235 → 底 0.045、顶 0.515，不再穿出脚底（简报原 -0.17 会把小腿垂到 -0.275 穿地）
  for (const s of [-1, 1]) {
    const upName = s < 0 ? 'LeftUpperLeg' : 'RightUpperLeg'
    const lowName = s < 0 ? 'LeftLowerLeg' : 'RightLowerLeg'
    const footName = s < 0 ? 'LeftFoot' : 'RightFoot'
    const upLeg = makePart(new CapsuleGeometry(0.08, 0.34, 6, 16), pantsMat, bones[upName], new Vector3(0, -0.17, 0))
    const lowLeg = makePart(new CapsuleGeometry(0.065, 0.34, 6, 16), pantsMat, bones[lowName], new Vector3(0, 0.15, 0))
    const foot = makePart(new SphereGeometry(0.065, 12, 12), pantsMat, bones[footName], new Vector3(0, -0.005, 0.02))
    group.add(upLeg, lowLeg, foot)
  }

  // 头发（男士短发贴片 / 女士长发垂片）
  const hairGeo = gender === 'male'
    ? new LatheGeometry([new Vector2(0.1, 0), new Vector2(0.14, 0.05), new Vector2(0.14, 0.12), new Vector2(0.12, 0.16)], 24)
    : new LatheGeometry([new Vector2(0.11, 0), new Vector2(0.15, 0.06), new Vector2(0.15, 0.2), new Vector2(0.13, 0.3)], 24)
  hairGeo.computeVertexNormals()
  const hairMesh = makePart(hairGeo, hairMat, bones.Head, new Vector3(0, 0.09, -0.005))

  group.add(headMesh, torsoMesh, hairMesh, root)

  // 初始化骨骼世界矩阵：makePart 在骨骼挂树前 bind，骨骼 matrixWorld 仍为 identity，
  // 不刷新则 SkinnedMesh 包围盒/射线/首次渲染会把网格错放到局部原点（脚底掉到 y<0）。
  group.updateMatrixWorld(true)

  const mixer = new AnimationMixer(group)
  return { group, skeleton, mixer }
}
