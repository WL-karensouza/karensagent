/* 自选股轮播工具函数 */

/* 指示点数量 = 可滑动位置数（与左右按钮步数一一对应），下限 1 */
export function slideDotCount(total, visible) {
  return Math.max(1, total - visible + 1)
}
