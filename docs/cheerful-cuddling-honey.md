# 3D 交互式办公室首页 — 实施计划（V1 简化版 · 对齐 V3.0）

## 修订记录

- **2026-07-28** V1 全程实施完成（场景/小人/交互/路由均验证通过），实测修正计划多处与 TresJS v5.8.3 不符之处：
  - three 版本：0.170 缺 `THREE.Timer` 不可用 → 最终锁定 **0.179.0**。
  - 新增 **1.1.1 节**：`vite.config.js` 必须配置 `templateCompilerOptions`（第一大坑，缺失则场景全崩）。
  - 相机：`:camera` prop 只接受相机实例，传配置对象会崩 → 改用 `<TresPerspectiveCamera>` 子元素。
  - 渲染循环：v5 为 `useLoop().onRender`（非 `useRenderLoop().onLoop`）。
  - 事件名：`@pointer-out`（非 `@pointer-leave`），事件可从子 mesh 冒泡到父 Group。
  - App.vue 全屏判断：`main` 在插槽作用域外，须用 `useRoute()`（原 5.2 把插槽 `route` 给 `main` 用是错的）。
  - 首页追加「操作提示」浮层（场景就绪后浮现、5 秒淡出）。
- **2026-07-27** 王磊哥哥指示，对齐 V3.0 重构后的项目现状，全文重写：
  - GitHub 热榜已于 V3.0 取消，替换为 **AI 前沿咨询**（agent id: `ai_news`），路由为 `/agent/ai_news`，旧文档中的 `/agent/github` 全部作废。
  - 修正 OfficeScene → OfficeHome 的事件流（emit 模式），旧文档中 OfficeScene 直接调用 OfficeHome 函数属错误写法。
  - 修正 `.main-content` 全局样式与全屏 3D 场景的冲突。
  - Phase 编号改为 V1 顺序 1~5，V2 内容统一归档到文末。
  - 新增依赖兼容性验证（Vite 8 + TresJS）与 three 版本锁定。
- 2026-07-25 初版确认的边界（仍然有效）：
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

将当前 `Home.vue`（Agent 卡片网格）替换为一个交互式 3D 办公室场景。场景包含：开放式办公室、两张办公桌、两个工作人员（**AI 前沿咨询** & **股票分析**）、墙面大屏占位。点击工作人员跳转到对应 Agent 页面。这是平台的视觉升级，保留全部现有路由和功能。

**V1 核心目标**：用户打开首页能看到一个可旋转、可缩放、可点击的 3D 办公室，小人会坐着打字，大屏看起来像个未加载数据的电视。

### 项目现状速查（V3.0）

| 项 | 值 |
|----|----|
| Agent 1 | **AI 前沿**，id=`ai_news`，路由 `/agent/ai_news`，LangGraph + Tavily + DeepSeek，每日推送飞书 |
| Agent 2 | **股票分析**，id=`stock`，路由 `/agent/stock`，iFinD SKILL 10 维度 + DeepSeek，SSE 流式报告 |
| 前端技术栈 | Vue `^3.5.38` / Vite `^8.1.4` / Pinia `^3.0.4` / vue-router `^4.6.4`（hash 模式）/ axios |
| 首页路由 | `/` → `views/Home.vue`（待替换） |
| 导航高度 | TopNav 主导航 64px，Agent 子导航 +45px，由 `TopNav.vue` 动态写入 CSS 变量 `--topnav-height` |
| 全局布局 | `.main-content` 有 `margin-top: var(--topnav-height)` + `max-width: 1280px` + `padding: 40px 48px` |

---

## V1 实施范围

| V1 Phase | 内容 | 是否包含 |
|----------|------|---------|
| Phase 1 | 安装 Three.js / TresJS 依赖 + 兼容性验证 | ✅ |
| Phase 2 | 3D 静态场景（房间、桌子、装饰物、占位大屏、名牌） | ✅ |
| Phase 3 | 工作人员几何体占位 + 打字动画 | ✅（仅打字，不含走动） |
| Phase 4 | 点击跳转 + OrbitControls 交互 + 悬浮反馈 | ✅ |
| Phase 5 | 替换 `Home.vue` 路由 + 禁用全局切换动画 | ✅ |
| — | 后端 `/api/stock/sectors` 板块数据接口 | ❌ V2 |
| — | 数据轮询 + 大屏 CanvasTexture 动态渲染 | ❌ V2 |
| — | 小人走动交流状态机 | ❌ V2 |

---

## Phase 1：依赖安装 & 兼容性验证

### 1.1 安装 Three.js 生态

```bash
cd d:\karensAgent\frontend
npm install three@0.179.0 @tresjs/core @tresjs/cientos
```

- `three` — 底层 3D 引擎（**锁定大版本**，避免 TresJS peer dependency 不匹配）
- `@tresjs/core` — Vue 3 声明式 Three.js 绑定
- `@tresjs/cientos` — 预置 `OrbitControls`、`Html` 等辅助组件

> ⚠️ **版本说明（实测结论，2026-07-28）**：`@tresjs/core@5.8.3` 的 peer 范围虽写 `three >=0.133`（很宽，npm 不报冲突），但其代码实际使用 `new THREE.Timer()`，而 **`THREE.Timer` 是 three r171+ 才引入的**。实测 `three@0.170.0` 会在运行时报 `THREE.Timer is not a constructor`（build 阶段为 `IMPORT_IS_UNDEFINED: Timer` 警告），**0.170 确定不可用**。最终锁定 **`three@0.179.0`**（满足 Timer、与 core@5.8.3 同期、早于 r180 的模块拆分重构），已端到端验证可用。0.180+ 引入 `three.module.js → three.core.js` 拆分，未在本项目验证，暂不采用。

### 1.1.1 vite.config.js 必需配置（TresJS 模板编译器）⚠️ 第一大坑

**缺了这一步，所有 `Tres*` 标签会被 Vue 当成未知组件解析失败，场景空白、渲染循环连环崩溃（`camera is not an instance of THREE.Camera` / `updateWorldMatrix is not a function`）。** 必须把 `@tresjs/core` 导出的 `templateCompilerOptions` 传给 `@vitejs/plugin-vue`：

```js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { templateCompilerOptions } from '@tresjs/core'

export default defineConfig({
  plugins: [
    vue({ ...templateCompilerOptions }),
  ],
  // ...其余 server / test 配置不变
})
```

### 1.2 兼容性验证（Vite 8 风险点）

项目使用 **Vite 8.1.4**，较新；`@tresjs/core` 官方验证通常覆盖到 Vite 5/6。安装后**必须**依次验证：

```bash
npm run dev      # 1. 开发服务器启动无报错
# 浏览器打开 http://localhost:5173/#/ ，确认现有页面正常
npm run build    # 2. 生产构建通过
npm run test     # 3. 现有测试不回归
```

**降级预案**：若 TresJS 与 Vite 8 不兼容，按以下顺序处理：
1. 优先：保留 Vite 8，改用**原生 Three.js**（不引入 TresJS），手写 `onMounted` 初始化 scene/renderer。本计划其余部分（场景结构、动画、交互逻辑）不变，仅组件写法从声明式改为命令式。
2. 备选：将 Vite 降级到 6.x，保留 TresJS。

### 1.3 新建目录结构

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

## Phase 2：3D 静态场景

### 2.1 OfficeRoom.vue — 房间结构

- **地板**：14×10 浅木色平面，`[-Math.PI/2,0,0]` 旋转，接收阴影。
- **后墙**：大型浅色平面，带 2-3 个发光窗户。
- **侧墙**：半高（留空天花板方便俯视）。
- **灯光**：
  - `AmbientLight(0.5)` — 基础环境光
  - `DirectionalLight` — 模拟窗外阳光，产生阴影
  - `PointLight` — 暖色顶灯，增加氛围
- **阴影**：所有主要物体开启 `cast-shadow` / `receive-shadow`；抗锯齿 `antialias` 开启。

### 2.2 OfficeDesk.vue — 办公桌（复用两次）

- 桌面：`BoxGeometry`，浅木色
- 桌腿：4 根细金属柱
- 显示器：黑色扁盒 + 微弱发光的蓝色屏幕（静态）
- 键盘：银色薄片
- 椅子：深灰色座位 + 靠背 + 金属底座圆柱

颜色方案（与平台现有配色呼应）：
- AI 前沿区域：平台主题橙 `#D97706` 点缀（`--accent`）
- 股票分析区域：深蓝 `#1a1a2e`（与现有 `StockDashboard` 图标底色一致）

### 2.3 OfficeDecorations.vue — 装饰物

- 绿植（角落）：圆柱花盆 + 绿色球体簇
- 咖啡机（靠墙）
- 白板（侧墙）
- 书架（靠墙）
- 地毯：桌子下方暖色平面

### 2.4 OfficeWallScreen.vue — 墙面大屏占位

- 深色金属边框大矩形。
- 屏幕区域使用 **CanvasTexture** 渲染静态占位图：
  - 暗色背景 `#0a1628`
  - 标题栏 "A股板块实时行情"
  - 三列灰色占位条（模拟未来数据行）
  - 底部状态栏 "数据加载中..."

**说明**：V1 屏幕内容写死，不读取后端数据，也不每 30 秒更新。CanvasTexture 中的中文使用系统字体渲染（Canvas 2D API），无需引入字体文件。

### 2.5 OfficeNameplate.vue — 地面工位名牌

- 每个工位前方地面放置一个扁平名牌。
- 文字（**与 `stores/agent.js` 中的 label 保持一致**）：
  - 左侧工位：`AI 前沿`
  - 右侧工位：`股票分析`
- 使用 CanvasTexture 生成文字贴图。

### 2.6 OfficeScene.vue — 场景组合根组件

```vue
<script setup>
import { TresCanvas } from '@tresjs/core'
import { OrbitControls } from '@tresjs/cientos'
import OfficeRoom from './OfficeRoom.vue'
import OfficeDesk from './OfficeDesk.vue'
import OfficeWorker from './OfficeWorker.vue'
import OfficeNameplate from './OfficeNameplate.vue'
import OfficeWallScreen from './OfficeWallScreen.vue'
import OfficeDecorations from './OfficeDecorations.vue'

/* 事件向上抛给 OfficeHome 处理，本组件不直接操作路由 */
const emit = defineEmits(['go-agent', 'ready'])

function onWorkerClick(agentId) {
  emit('go-agent', agentId)
}
function onSceneReady() {
  emit('ready')
}
</script>

<template>
  <TresCanvas
    shadows
    antialias
    @ready="onSceneReady"
  >
    <!-- v5 相机必须用子元素声明（:camera prop 只收相机实例，传配置对象会崩） -->
    <TresPerspectiveCamera :position="[0, 6, 6]" :fov="55" />
    <OrbitControls
      :enableDamping="true"
      :minDistance="4"
      :maxDistance="16"
      :maxPolarAngle="Math.PI / 2.5"
      :target="[0, 0, -1]"
    />
    <OfficeRoom />
    <OfficeDecorations />

    <!-- AI 前沿工位（左侧） → /agent/ai_news -->
    <OfficeDesk :position="[-3, 0, -2]" theme="ai_news" />
    <OfficeWorker worker-id="ai_news" :position="[-3, 0, -2]" @click="onWorkerClick('ai_news')" />
    <OfficeNameplate :position="[-3, 0.02, -0.6]" text="AI 前沿" />

    <!-- 股票分析工位（右侧） → /agent/stock -->
    <OfficeDesk :position="[3, 0, -2]" theme="stock" />
    <OfficeWorker worker-id="stock" :position="[3, 0, -2]" @click="onWorkerClick('stock')" />
    <OfficeNameplate :position="[3, 0.02, -0.6]" text="股票分析" />

    <OfficeWallScreen :position="[0, 2.2, -4.8]" />
  </TresCanvas>
</template>
```

> **事件流约定**：`OfficeWorker @click` → `OfficeScene.emit('go-agent', id)` → `OfficeHome.goAgent(id)` → `router.push`。路由操作只发生在 `OfficeHome`，场景组件不感知 router。

---

## Phase 3：工作人员（V1 仅打字动画）

### 3.1 几何体占位模型

```
身体：BoxGeometry [0.3, 0.4, 0.2]（躯干）
头部：SphereGeometry radius=0.12
手臂：细 BoxGeometry ×2，向前伸展（打字姿态）
腿部：细 BoxGeometry ×2，向前延伸（坐姿）
```

### 3.2 打字动画

在 `useLoop().onRender` 中用 `sin` 振荡手臂旋转角，模拟敲击键盘：

- 振幅：±0.05 弧度
- 频率：约 4Hz
- 左右手臂相位错开，看起来更自然

```js
// composables/useWorkerAnimation.js
// 注意：v5 渲染循环 composable 是 useLoop，回调钩子是 onRender（不是 useRenderLoop/onLoop）
import { useLoop } from '@tresjs/core'

/* 模板 ref 解包：兼容裸 three 对象与 Tres 包装器两种返回 */
function toThree(refValue) {
  if (!refValue) return null
  return refValue.__tres?.object ?? refValue
}

export function useWorkerAnimation(leftArm, rightArm) {
  const { onRender } = useLoop()
  onRender(({ elapsed }) => {
    const left = toThree(leftArm.value)
    const right = toThree(rightArm.value)
    if (!left || !right) return
    left.rotation.x = Math.sin(elapsed * 8) * 0.05
    right.rotation.x = Math.sin(elapsed * 8 + Math.PI) * 0.05
  })
}
```

---

## Phase 4：交互

- **点击工人**：`goAgent('ai_news')` / `goAgent('stock')` → `router.push('/agent/xxx')`
- **OrbitControls**：左键旋转、滚轮缩放、右键平移
- **悬浮效果**：`@pointer-over` 放大 1.05× + `cursor: pointer`

> TresJS 事件名与 DOM 略有差异，V1 使用 `@pointer-over` / `@pointer-out` / `@click`（**没有 `@pointer-leave`**；事件可从子 mesh 冒泡到父 Group，故交互绑在根 Group 即可）。

---

## Phase 5：替换 Home.vue

### 5.1 新建 OfficeHome.vue

```vue
<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import OfficeScene from '../components/office/OfficeScene.vue'

const router = useRouter()
const ready = ref(false)
const webglOk = ref(true)

/* 唯一的路由出口：场景组件只抛事件，不碰 router */
function goAgent(id) {
  router.push(`/agent/${id}`)
}
function onSceneReady() {
  ready.value = true
}

/* WebGL 可用性检测，不可用时降级为 HTML 入口卡片 */
onMounted(() => {
  try {
    const canvas = document.createElement('canvas')
    webglOk.value = !!(canvas.getContext('webgl2') || canvas.getContext('webgl'))
  } catch {
    webglOk.value = false
  }
})
</script>

<template>
  <div class="office-home">
    <!-- WebGL 不可用：降级为纯 HTML 入口 -->
    <div v-if="!webglOk" class="webgl-fallback">
      <p>当前浏览器不支持 3D 渲染，请通过下方入口访问：</p>
      <div class="fallback-links">
        <button class="btn btn-primary" @click="goAgent('ai_news')">AI 前沿</button>
        <button class="btn btn-primary" @click="goAgent('stock')">股票分析</button>
      </div>
    </div>

    <!-- 正常路径：3D 场景 -->
    <template v-else>
      <Transition name="fade">
        <div v-if="!ready" class="loading-fallback">
          <div class="spinner" />
          <p>加载 3D 场景中...</p>
        </div>
      </Transition>
      <OfficeScene @ready="onSceneReady" @go-agent="goAgent" />
    </template>
  </div>
</template>

<style scoped>
/* 全屏 3D 容器：挣脱 .main-content 的 1280px 居中与 padding 约束 */
.office-home {
  position: fixed;
  inset: 0;
  top: var(--topnav-height, 64px);
}

/* 加载占位 */
.loading-fallback {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--text-muted);
  font-size: 0.9rem;
}

/* WebGL 降级入口 */
.webgl-fallback {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 20px;
  color: var(--text-secondary);
}
.fallback-links {
  display: flex;
  gap: 16px;
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

> **布局说明**：OfficeHome 渲染在 `.main-content` 内部，但 `position: fixed` 使其脱离文档流、相对视口定位，`top: var(--topnav-height)` 自动避让 TopNav（首页无子导航时该值为 `64px`）。fixed 定位不受父级 `max-width` / `padding` 约束，因此天然全屏。

### 5.2 消除多余滚动条（App.vue）

`.main-content` 的 `padding: 40px 48px` 会在首页撑出滚动区域。在 `App.vue` 中根据路由 meta 条件去掉：

```vue
<!-- App.vue -->
<script setup>
import { useRoute } from 'vue-router'
const route = useRoute() /* main 在 router-view 插槽外，必须用 useRoute() 拿 route */
</script>

<main class="main-content" :class="{ 'is-fullscreen': route.meta.noPageTransition }">
  <router-view v-slot="{ Component }">
    <transition v-if="!route.meta.noPageTransition" name="page" mode="out-in">
      <component :is="Component" />
    </transition>
    <component v-else :is="Component" />
  </router-view>
</main>
```

```css
/* App.vue scoped */
.main-content.is-fullscreen {
  max-width: none;
  padding: 0;
  margin-top: 0;
}
```

> 注意：`main` 标签在 `router-view` **插槽作用域之外**，拿不到插槽里的 `route`，所以必须在 `<script setup>` 里用 `useRoute()` 获取当前路由（原稿把 `route` 解构进插槽再给 `main` 用是错的，已修正）。

### 5.3 修改路由

`frontend/src/router/index.js`：

```diff
  {
    path: '/',
    name: 'home',
-   component: () => import('../views/Home.vue'),
-   meta: { title: 'Agent 控制台' },
+   component: () => import('../views/OfficeHome.vue'),
+   meta: { title: 'Agent 控制台', noPageTransition: true },
  },
```

### 5.4 旧首页备份

- 将 `frontend/src/views/Home.vue` **重命名**为 `frontend/src/views/HomeLegacy.vue`。
- 不删除，作为备份保留。
- `Home.vue` 的样式是 `<style scoped>`，无全局样式泄漏；`style.css` 中无需清理。

---

## V2 待办（第二版再实现）

1. **后端 `/api/stock/sectors` 接口**
   - 优先使用 iFinD `index.sector_data` 自然语言查询申万一级行业涨跌幅排名。
   - 不稳定时降级为 `index.index_highfreq_quotes` 查三大指数。
   - 30 秒内存缓存。

2. **前端数据轮询**
   - 新建 `frontend/src/stores/office.js`。
   - `OfficeScene.vue` `onMounted` 启动轮询，每 30 秒拉取一次。
   - `OfficeWallScreen.vue` 改为动态 CanvasTexture，根据数据重绘。

3. **小人走动交流动画**
   - 扩展 `useWorkerAnimation.js` 为状态机：`seated → standingUp → walking → gesturing → walkingBack → sittingDown → seated`。
   - 60-120 秒随机触发，每段过渡 2 秒（`easeInOutCubic`），工位 A (x=-3) ↔ 工位 B (x=3)。

4. **glTF 模型替换**
   - 把 `OfficeWorker.vue` 中的几何体替换为 `<GLTFModel path="/models/worker.glb" />`，prop 接口不变。

---

## V1 实施顺序

| 顺序 | Phase | 可独立验证 |
|------|-------|-----------|
| 1 | Phase 1 — 安装依赖 + 兼容性验证 | `npm run dev` / `npm run build` / `npm run test` 全绿 |
| 2 | Phase 2 — 静态场景 | 浏览器看到空办公室 + 占位大屏 + 名牌 |
| 3 | Phase 3 — 工人 | 看到两个小人 + 打字动画 |
| 4 | Phase 4 — 交互 | 点击跳转 + 轨道控制 + 悬浮放大 |
| 5 | Phase 5 — 路由切换 + 布局收尾 | `/` 显示 3D 场景，旧卡片页面作为 `HomeLegacy.vue` 保留 |

---

## V1 验证清单

- [ ] `npm run build` 无报错
- [ ] `npm run test` 现有测试不回归
- [ ] 浏览器访问 `http://localhost:5173/#/` 看到 3D 办公室
- [ ] 摄像机初始角度为 45° 斜俯视，两工位和墙面大屏均可见
- [ ] 鼠标可旋转 / 缩放 / 平移
- [ ] 两个工人坐在各自工位，手臂轻微抖动（打字）
- [ ] 墙面大屏显示静态标题和灰色占位条
- [ ] 左侧名牌 "AI 前沿"、右侧名牌 "股票分析"
- [ ] 点击左侧工人跳转到 `/agent/ai_news`，右侧跳转到 `/agent/stock`
- [ ] 悬浮工人时放大 1.05× 且鼠标变 pointer
- [ ] TopNav 各标签和 logo 点击正常，子导航高度变化不影响 3D 场景
- [ ] `/agent/ai_news`、`/agent/stock` 等现有页面无回归
- [ ] `OfficeHome` 进入时没有全局上下滑入动画
- [ ] 首页无多余滚动条
- [ ] 加载 3D 场景时出现 spinner，加载完成后消失
- [ ] 禁用 WebGL 的浏览器显示降级入口卡片，可正常跳转
- [ ] 窗口 resize 后 3D 场景自适应
- [ ] 60fps 稳定运行（DevTools FPS 检查）
