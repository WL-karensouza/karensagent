<script setup>
/* ═══════════════════════════════════════════
   OfficeRoom —— 房间结构：灯光系统 + 地板 + 墙体 + 窗户
   浅色国际配色，阴影 / 抗锯齿由 TresCanvas 统一开启
   ═══════════════════════════════════════════ */
/* DoubleSide：墙双面可见，配合相机横向 360° 旋转，绕到墙外背面也不穿帮 */
import { DoubleSide, TextureLoader, RepeatWrapping, SRGBColorSpace, NoColorSpace, Vector2 } from 'three'
import { markRaw } from 'vue'

/* ══ 地板 PBR 贴图（ambientCG WoodFloor036，CC0） ══
   TextureLoader.load 同步返回 Texture 对象（图片后台解码，three 解码完自动重绘），
   故无需 ref；再 markRaw 标记，杜绝 Vue 深代理 three 对象导致渲染崩溃（modelViewMatrix 报错）。
   色彩空间：颜色图 sRGB、法线/粗糙度线性；三张统一 RepeatWrapping + 按地板长宽比平铺防拉伸 */
const FLOOR_W = 14
const FLOOR_D = 10
const FLOOR_TILE = 2 /* 一块贴图覆盖的世界米数（资产标称≈1.9m，取 2 便于整除且木纹尺寸真实，可调） */

const loader = new TextureLoader()

function loadFloorMap(url, isColor) {
  const tex = loader.load(url)
  tex.wrapS = tex.wrapT = RepeatWrapping
  tex.repeat.set(FLOOR_W / FLOOR_TILE, FLOOR_D / FLOOR_TILE)
  tex.colorSpace = isColor ? SRGBColorSpace : NoColorSpace
  return markRaw(tex)
}

const floorColor = loadFloorMap('/models/textures/WoodFloor_Color.jpg', true)
const floorNormal = loadFloorMap('/models/textures/WoodFloor_NormalGL.jpg', false)
const floorRough = loadFloorMap('/models/textures/WoodFloor_Roughness.jpg', false)
/* 法线强度：0.5 让人字拼缝隙凹凸柔和，不显塑料感（用 Vector2 常量绑定，避免数组转换的不确定性） */
const floorNormalScale = markRaw(new Vector2(0.5, 0.5))
</script>

<template>
  <TresGroup>
    <!-- ══ 灯光系统 ══ -->
    <!-- 环境光：基础照明，避免死黑 -->
    <TresAmbientLight :intensity="0.6" />
    <!-- 半球光：天空白 / 地面暖木色，柔和过渡 -->
    <TresHemisphereLight :intensity="0.4" color="#ffffff" ground-color="#E8D5B7" />
    <!-- 主方向光：模拟窗外阳光，场景中唯一产生阴影的光源 -->
    <TresDirectionalLight
      :position="[6, 11, 7]"
      :intensity="1.4"
      color="#fff4e0"
      cast-shadow
      :shadow-mapSize-width="2048"
      :shadow-mapSize-height="2048"
      :shadow-camera-left="-10"
      :shadow-camera-right="10"
      :shadow-camera-top="10"
      :shadow-camera-bottom="-10"
      :shadow-camera-near="0.5"
      :shadow-camera-far="40"
      :shadow-bias="-0.0004"
    />
    <!-- 暖色顶灯：增加室内氛围（物理光照单位，decay 衰减） -->
    <TresPointLight :position="[0, 4.2, 0]" :intensity="6" color="#ffd9a0" :distance="16" :decay="2" />

    <!-- ══ 地板（浅木色，接收阴影） ══ -->
    <TresMesh :rotation="[-Math.PI / 2, 0, 0]" receive-shadow>
      <TresPlaneGeometry :args="[14, 10]" />
      <!-- PBR 木地板：颜色/法线/粗糙度三贴图；roughness=1 让粗糙度图完全主导；metalness=0 木头不金属 -->
      <TresMeshStandardMaterial
        :map="floorColor"
        :normal-map="floorNormal"
        :roughness-map="floorRough"
        :normal-scale="floorNormalScale"
        :roughness="1"
        :metalness="0"
      />
    </TresMesh>

    <!-- ══ 后墙（DoubleSide：双面可见，360° 绕到背面不穿帮） ══ -->
    <TresMesh :position="[0, 2.5, -5]" receive-shadow>
      <TresPlaneGeometry :args="[14, 5]" />
      <TresMeshStandardMaterial color="#F2EFE9" :roughness="0.95" :side="DoubleSide" />
    </TresMesh>

    <!-- ══ 侧墙（全高围合；DoubleSide 双面可见） ══ -->
    <TresMesh :rotation="[0, Math.PI / 2, 0]" :position="[-7, 2.5, 0]" receive-shadow>
      <TresPlaneGeometry :args="[10, 5]" />
      <TresMeshStandardMaterial color="#EDE8DF" :roughness="0.95" :side="DoubleSide" />
    </TresMesh>
    <TresMesh :rotation="[0, -Math.PI / 2, 0]" :position="[7, 2.5, 0]" receive-shadow>
      <TresPlaneGeometry :args="[10, 5]" />
      <TresMeshStandardMaterial color="#EDE8DF" :roughness="0.95" :side="DoubleSide" />
    </TresMesh>

    <!-- ══ 前墙（补全围合；DoubleSide 双面可见） ══ -->
    <TresMesh :rotation="[0, Math.PI, 0]" :position="[0, 2.5, 5]" receive-shadow>
      <TresPlaneGeometry :args="[14, 5]" />
      <TresMeshStandardMaterial color="#EDE8DF" :roughness="0.95" :side="DoubleSide" />
    </TresMesh>

    <!-- ══ 后墙发光窗户 ×2（纯装饰，模拟采光） ══ -->
    <TresMesh :position="[-4, 2.6, -4.95]">
      <TresPlaneGeometry :args="[2, 1.6]" />
      <TresMeshBasicMaterial color="#cfe8ff" />
    </TresMesh>
    <TresMesh :position="[4, 2.6, -4.95]">
      <TresPlaneGeometry :args="[2, 1.6]" />
      <TresMeshBasicMaterial color="#cfe8ff" />
    </TresMesh>
  </TresGroup>
</template>
