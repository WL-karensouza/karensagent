/* ═══════════════════════════════════════════
   useModel —— glTF 模型加载与归一化
   基于 @tresjs/cientos 的 useGLTF：它返回「响应式 state」而非 Promise，
   加载完成后 state.value.scene 才被填充，失败写入 error ref。
   故加载必须用 watch 驱动，绝不能 await useGLTF（await 非 thenable 会得到对象本身，
   解构 scene 必为 undefined → 模型与兜底都不渲染，整片空白）。
   ═══════════════════════════════════════════ */
import { ref, shallowRef, watch } from 'vue'
import { useGLTF } from '@tresjs/cientos'
import { Box3, Vector3 } from 'three'

/**
 * 模型归一化：缩放 → 水平居中/落地对齐 → 阴影
 * @param {import('three').Object3D} root glTF 的 scene 根节点
 * @param {object} [options]
 * @param {number|number[]} [options.size] 目标尺寸：数字=按最长边适配（米）；[w,h,d]=各轴独立适配
 * @param {boolean} [options.center=true] 是否把模型 xz 中心移到原点（外部模型原点常有偏移，不居中则摆放不可控）
 * @param {boolean} [options.ground=true] 是否把模型底部对齐到 y=0
 * @param {boolean} [options.shadow=true] 是否统一开启 castShadow / receiveShadow
 */
export function normalizeModel(root, { size = null, center = true, ground = true, shadow = true } = {}) {
  if (!root) return

  /* ── 缩放：按缩放前包围盒尺寸推导比例 ── */
  if (size != null) {
    const box = new Box3().setFromObject(root)
    const dim = box.getSize(new Vector3())
    if (Array.isArray(size)) {
      root.scale.set(size[0] / dim.x, size[1] / dim.y, size[2] / dim.z)
    } else {
      root.scale.setScalar(size / Math.max(dim.x, dim.y, dim.z))
    }
  }

  /* ── 摆放：缩放后重算包围盒，xz 居中 + 底部对齐 y=0（xz 平移不影响 y，一次包围盒即可） ── */
  if (center || ground) {
    const box = new Box3().setFromObject(root)
    if (center) {
      const c = box.getCenter(new Vector3())
      root.position.x -= c.x
      root.position.z -= c.z
    }
    if (ground) {
      root.position.y -= box.min.y
    }
  }

  /* ── 阴影：遍历所有网格统一开启 ── */
  if (shadow) {
    root.traverse((child) => {
      if (child.isMesh) {
        child.castShadow = true
        child.receiveShadow = true
      }
    })
  }
}

/**
 * 加载 glTF 并归一化，返回响应式 { modelScene, loadError }
 * 须在组件 setup 同步栈内调用（内部用 useGLTF / watch）
 * 注：每个调用各自独立加载，多实例不复用同一 scene，故无需 clone
 * @param {string} src 模型路径，如 '/models/furniture/desk_workstation.glb'
 * @param {object} [options]
 * @param {number|number[]} [options.size] 透传给 normalizeModel 的目标尺寸
 */
export function useModel(src, { size = null, prepare = null } = {}) {
  /* 必须 shallowRef：three 对象绝不能进 Vue 深度 reactive，否则 mesh.matrix 等
     不可配置属性被代理，渲染时触发 Proxy 不变量抛错（modelViewMatrix read-only 报错）。
     shallowRef 只代理 .value 引用本身，gltf.scene 子树保持裸 three 对象。 */
  const modelScene = shallowRef(null)
  const loadError = ref(false)

  /* useGLTF 返回响应式 state（gltf 对象，含 .scene）与 error ref */
  const { state, error } = useGLTF(src)

  /* 加载成功：state 出现 scene → 归一化并暴露（守卫仅处理首次，避免重复归一化） */
  watch(state, (gltf) => {
    if (gltf?.scene && !modelScene.value) {
      normalizeModel(gltf.scene, { size })
      /* 归一化后、挂载前交给业务做场景级微调（如拆开椅子节点） */
      prepare?.(gltf.scene)
      modelScene.value = gltf.scene
    }
  }, { immediate: true })

  /* 加载失败：error 被置位 → 触发降级（调用方据此渲染 fallback 插槽） */
  watch(error, (err) => {
    if (err) {
      loadError.value = true
      console.warn(`[useModel] 模型加载失败，降级为几何体兜底: ${src}`, err)
    }
  }, { immediate: true })

  return { modelScene, loadError }
}
