import { describe, it, expect } from 'vitest'
import * as THREE from 'three' // 简报遗漏：Box3 需要 THREE 命名空间，此处补 import
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
