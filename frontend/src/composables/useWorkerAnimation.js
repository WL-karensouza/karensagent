/* ═══════════════════════════════════════════
   useWorkerAnimation —— 工人打字动画
   用渲染循环 sin 振荡左右手臂枢轴，模拟敲击键盘
   注：v5 渲染循环 composable 为 useLoop，回调钩子为 onRender
   ═══════════════════════════════════════════ */
import { useLoop } from '@tresjs/core'

/* 模板 ref 解包：兼容「裸 three 对象」与「Tres 包装器」两种返回 */
function toThree(refValue) {
  if (!refValue) return null
  return refValue.__tres?.object ?? refValue
}

/**
 * @param {import('vue').Ref} leftArm  左臂枢轴分组 ref
 * @param {import('vue').Ref} rightArm 右臂枢轴分组 ref
 */
export function useWorkerAnimation(leftArm, rightArm) {
  const { onRender } = useLoop()

  onRender(({ elapsed }) => {
    const left = toThree(leftArm.value)
    const right = toThree(rightArm.value)
    if (!left || !right) return

    /* 振幅 ±0.05 弧度、角频率 8（约 4Hz）、左右相位错开更自然 */
    left.rotation.x = Math.sin(elapsed * 8) * 0.05
    right.rotation.x = Math.sin(elapsed * 8 + Math.PI) * 0.05
  })
}
