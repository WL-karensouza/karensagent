# 3D 交互式办公室首页 — 实施计划（V1 简化版）

## 修订记录

- 2026-07-25 与王磊哥哥确认后调整：
  - V1 只做 3D 静态场景 + 打字小人 + 点击跳转 + 路由替换，**不做后端数据接口**。
  - 墙面大屏先占位：只显示静态标题和灰色占位条，**不展示真实行情**。
  - 小人走动交流动画放到 V2；V1 只做坐着打字的动画。
  - 旧 `Home.vue` 重命名为 `HomeLegacy.vue` 作为备份。
  - 只保留两个工位，不预留第三个空位。
  - 每个人前面增加地面工位名牌。
  - 阴影和抗锯齿全开。
  - 加载 fallback 用 spinner，通过 `TresCanvas @ready` 控制，不用 `Suspense`。
  - `OfficeHome.vue` 禁用 `App.vue` 全局页面切换动画。

---

## Context

将当前 `Home.vue`（Agent 卡片网格）替换为一个交互式 3D 办公室场景。场景包含：开放式办公室、两张办公桌、两个工作人员（GitHub 热榜爬虫 & 股票交易员）、墙面大屏占位。点击工作人员跳转到对应 Agent 页面。这是平台的视觉升级，保留全部现有路由和功能。

**V1 核心目标**：用户打开首页能看到一个可旋转、可缩放、可点击的 3D 办公室，小人会坐着打字，大屏看起来像个未加载数据的电视。

---

## V1 实施范围

| 阶段 | 内容 | 是否包含在 V1 |
|------|------|--------------|
| Phase 1 | 安装 Three.js / TresJS 依赖 | ✅ |
| Phase 3 | 3D 静态场景（房间、桌子、装饰物、占位大屏） | ✅ |
| Phase 4 | 工作人员几何体占位 + 打字动画 | ✅（仅打字，不含走动） |
| Phase 6 | 点击跳转 + OrbitControls 交互 | ✅ |
| Phase 7 | 替换 `Home.vue` 路由 | ✅ |
| Phase 2 | 后端 `/api/stock/sectors` 板块数据接口 | ❌ 放到 V2 |
| Phase 5 | 数据轮询 + 大屏 CanvasTexture 动态渲染 | ❌ 放到 V2 |
| Phase 4（走动） | 小人走动交流状态机 | ❌ 放到 V2 |

---

## Phase 1：依赖安装 & 文件骨架

### 1.1 安装 Three.js 生态

```bash
cd d:\karensAgent\frontend
npm install three @tresjs/core @tresjs/cientos
```

- `three` — 底层 3D 引擎
- `@tresjs/core` — Vue 3 声明式 Three.js 绑定
- `@tresjs/cientos` — 预置 `OrbitControls`、`Html` 等辅助组件

当前项目已使用 Vue `^3.5.38` 和 Vite `^8.1.4`，与 `@tresjs/core` 最新版兼容，**无需修改 `vite.config.js`**。

### 1.2 新建目录结构

```
frontend/src/
├── components/office/
│   ├── OfficeScene.vue          # TresCanvas 根组件，场景组合
│   ├── OfficeRoom.vue           # 地板、墙壁、窗户、灯光、阴影
│   ├── OfficeDesk.vue           # 单个办公桌 + 显示器 + 椅子（复用）
│   ├── OfficeWorker.vue         # 单个工作人员几何体占位
│   ├── OfficeWallScreen.vue     # 墙面大屏（静态占位纹理）
│   ├── OfficeNameplate.vue      # 地面工位名牌
│   └── OfficeDecorations.vue    # 绿植、咖啡机、白板、书架等
├── composables/
│   └── useWorkerAnimation.js    # 工人打字动画
└── views/
    └── OfficeHome.vue           # 新首页（替换 Home.vue）
```

**说明**：V1 暂不创建 `stores/office.js`，也不新增 `api/index.js` 中的 `getSectorData`。

---

## Phase 3：3D 静态场景

### 3.1 OfficeRoom.vue — 房间结构

- **地板**：14×10 浅木色平面，`[-Math.PI/2,0,0]` 旋转，接收阴影。
- **后墙**：大型浅色平面，带 2-3 个发光窗户。
- **侧墙**：半高（留空天花板方便俯视）。
- **灯光**：
  - `AmbientLight(0.5)` — 基础环境光
  - `DirectionalLight` — 模拟窗外阳光，产生阴影
  - `PointLight` — 暖色顶灯，增加氛围
- **阴影**：所有主要物体开启 `cast-shadow` / `receive-shadow`；抗锯齿 `antialias` 开启。

### 3.2 OfficeDesk.vue — 办公桌（复用两次）

- 桌面：`BoxGeometry`，浅木色
- 桌腿：4 根细金属柱
- 显示器：黑色扁盒 + 微弱发光的蓝色屏幕（静态）
- 键盘：银色薄片
- 椅子：深灰色座位 + 靠背 + 金属底座圆柱

颜色方案：
- 员工 1 区域（GitHub）：深色系 `#24292e`
- 员工 2 区域（股票）：深蓝色系 `#1a1a2e`

### 3.3 OfficeDecorations.vue — 装饰物

- 绿植（角落）：圆柱花盆 + 绿色球体簇
- 咖啡机（靠墙）
- 白板（侧墙）
- 书架（靠墙）
- 地毯：桌子下方暖色平面

### 3.4 OfficeWallScreen.vue — 墙面大屏占位

- 深色金属边框大矩形。
- 屏幕区域使用 **CanvasTexture** 渲染静态占位图：
  - 暗色背景 `#0a1628`
  - 标题栏 “A股板块实时行情”
  - 三列灰色占位条（模拟未来数据行）
  - 底部状态栏 “数据加载中...”

**说明**：V1 屏幕内容写死，不读取后端数据，也不每 30 秒更新。

### 3.5 OfficeNameplate.vue — 地面工位名牌

- 每个工位前方地面放置一个扁平名牌。
- 文字：
  - 左侧工位：`GitHub 热榜`
  - 右侧工位：`股票分析`
- 使用 CanvasTexture 生成文字贴图，避免引入字体文件。

### 3.6 OfficeScene.vue — 场景组合根组件

```html
<TresCanvas
  shadows
  antialias
  :camera="{ position: [0, 6, 6], fov: 55 }"
  @ready="onSceneReady"
>
  <OrbitControls
    :enableDamping="true"
    :minDistance="4"
    :maxDistance="16"
    :maxPolarAngle="Math.PI / 2.5"
    :target="[0, 0, -1]"
  />
  <OfficeRoom />
  <OfficeDecorations />

  <!-- GitHub 工位（左侧） -->
  <OfficeDesk :position="[-3, 0, -2]" theme="github" />
  <OfficeWorker worker-id="github" :position="[-3, 0, -2]" @click="goAgent('github')" />
  <OfficeNameplate :position="[-3, 0.02, -0.6]" text="GitHub 热榜" />

  <!-- 股票工位（右侧） -->
  <OfficeDesk :position="[3, 0, -2]" theme="stock" />
  <OfficeWorker worker-id="stock" :position="[3, 0, -2]" @click="goAgent('stock')" />
  <OfficeNameplate :position="[3, 0.02, -0.6]" text="股票分析" />

  <OfficeWallScreen :position="[0, 2.2, -4.8]" />
</TresCanvas>
```

---

## Phase 4：工作人员（V1 仅打字动画）

### 4.1 几何体占位模型

```
身体：BoxGeometry [0.3, 0.4, 0.2]（躯干）
头部：SphereGeometry radius=0.12
手臂：细 BoxGeometry ×2，向前伸展（打字姿态）
腿部：细 BoxGeometry ×2，向前延伸（坐姿）
```

### 4.2 打字动画

在 `useRenderLoop` 中用 `sin` 振荡手臂旋转角，模拟敲击键盘：

- 振幅：±0.05 弧度
- 频率：约 4Hz
- 左右手臂相位错开，看起来更自然

### 4.3 V2 才实现：走动交流动画

状态机：`seated → standingUp → walking → gesturing → walkingBack → sittingDown → seated`

- 随机间隔 60-120 秒触发
- 每段过渡 2 秒，使用 `easeInOutCubic`
- 走路路径：工位 A (x=-3) ↔ 工位 B (x=3)
- 交流阶段手臂上下摆动

### 4.4 glTF 模型替换策略

后续只需把 `OfficeWorker.vue` 中的几何体替换为 `<GLTFModel path="/models/worker.glb" />`，prop 接口不变。

---

## Phase 6：交互

- **点击工人**：`goAgent('github')` / `goAgent('stock')` → `router.push('/agent/xxx')`
- **OrbitControls**：左键旋转、滚轮缩放、右键平移
- **悬浮效果**：`@pointer-over` 放大 1.05× + `cursor: pointer`

> TresJS 事件名与 DOM 略有差异，V1 使用 `@pointer-over` / `@pointer-leave` / `@click`。

---

## Phase 7：替换 Home.vue

### 7.1 新建 OfficeHome.vue

```vue
<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import OfficeScene from '../components/office/OfficeScene.vue'

const router = useRouter()
const ready = ref(false)

function goAgent(id) {
  router.push(`/agent/${id}`)
}
function onSceneReady() {
  ready.value = true
}
</script>

<template>
  <div class="office-home">
    <Transition name="fade">
      <div v-if="!ready" class="loading-fallback">
        <div class="spinner" />
        <p>加载 3D 场景中...</p>
      </div>
    </Transition>
    <OfficeScene @ready="onSceneReady" @go-agent="goAgent" />
  </div>
</template>

<style scoped>
.office-home {
  position: fixed;
  inset: 0;
  top: var(--topnav-height, 64px);
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
```

### 7.2 修改路由

`frontend/src/router/index.js` 第 7 行：

```diff
- component: () => import('../views/Home.vue'),
+ component: () => import('../views/OfficeHome.vue'),
```

### 7.3 旧首页备份

- 将 `frontend/src/views/Home.vue` **重命名**为 `frontend/src/views/HomeLegacy.vue`。
- 不删除，作为备份保留。
- `style.css` 中仅 `HomeLegacy.vue` 使用的全局样式类（`.agent-card-grid` 等）暂不清理，等 V2 稳定后再处理。

### 7.4 禁用全局页面切换动画

`App.vue` 的 `page` transition 会让全屏 3D 场景整体滑入，效果不佳。`OfficeHome.vue` 通过路由 `meta` 或组件选项跳过该动画：

```js
// router/index.js
{
  path: '/',
  name: 'home',
  component: () => import('../views/OfficeHome.vue'),
  meta: { title: 'Agent 控制台', noPageTransition: true },
}
```

```vue
<!-- App.vue -->
<router-view v-slot="{ Component, route }">
  <transition
    v-if="!route.meta.noPageTransition"
    name="page"
    mode="out-in"
  >
    <component :is="Component" />
  </transition>
  <component v-else :is="Component" />
</router-view>
```

---

## V2 待办（第二版再实现）

1. **后端 `/api/stock/sectors` 接口**
   - 优先使用 `index.sector_data` 自然语言查询申万一级行业涨跌幅排名。
   - 不稳定时降级为 `index.index_highfreq_quotes` 查三大指数。
   - 30 秒内存缓存。

2. **前端数据轮询**
   - 新建 `frontend/src/stores/office.js`。
   - `OfficeScene.vue` `onMounted` 启动轮询，每 30 秒拉取一次。
   - `OfficeWallScreen.vue` 改为动态 CanvasTexture，根据数据重绘。

3. **小人走动交流动画**
   - 扩展 `useWorkerAnimation.js` 为状态机。
   - 60-120 秒随机触发，工位 A ↔ 工位 B 走动。

---

## V1 实施顺序

| 顺序 | Phase | 可独立验证 |
|------|-------|-----------|
| 1 | Phase 1 — 安装依赖 | `npm ls three @tresjs/core @tresjs/cientos` |
| 2 | Phase 3 — 静态场景 | 浏览器看到空办公室 + 占位大屏 |
| 3 | Phase 4 — 工人 | 看到两个小人 + 打字动画 |
| 4 | Phase 6 — 交互 | 点击跳转 + 轨道控制 |
| 5 | Phase 7 — 路由切换 | `/` 显示 3D 场景，旧卡片页面作为 `HomeLegacy.vue` 保留 |

---

## V1 验证清单

- [ ] `npm run build` 无报错
- [ ] 浏览器访问 `http://localhost:5173/#/` 看到 3D 办公室
- [ ] 摄像机初始角度为 45° 斜俯视，两工位和墙面大屏均可见
- [ ] 鼠标可旋转 / 缩放 / 平移
- [ ] 两个工人坐在各自工位，手臂轻微抖动（打字）
- [ ] 墙面大屏显示静态标题和灰色占位条
- [ ] 每个工位前方有地面名牌
- [ ] 点击工人跳转到对应 Agent 子页面
- [ ] TopNav 各标签和 logo 点击正常
- [ ] `/agent/github`、`/agent/stock` 等现有页面无回归
- [ ] `OfficeHome` 进入时没有全局上下滑入动画
- [ ] 加载 3D 场景时出现 spinner，加载完成后消失
- [ ] 60fps 稳定运行（DevTools FPS 检查）
