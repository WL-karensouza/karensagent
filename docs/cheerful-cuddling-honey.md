# 3D 交互式办公室首页 — 实施计划

## Context

将当前 Home.vue（Agent 卡片网格）替换为一个交互式 3D 办公室场景。场景包含：开放式办公室、两张办公桌、两个工作人员（GitHub 热榜爬虫 & 股票交易员）、墙面大屏动态展示 A 股板块数据。点击工作人员跳转到对应 Agent 页面。这是平台的视觉升级，保留全部现有路由和功能。

---

## Phase 1：依赖安装 & 文件骨架

### 1.1 安装 Three.js 生态

```bash
cd d:\karensAgent\frontend
npm install three @tresjs/core @tresjs/cientos
```

- `three` — 底层 3D 引擎
- `@tresjs/core` — Vue 3 声明式 Three.js 绑定
- `@tresjs/cientos` — 预置 OrbitControls、GLTFModel 等

无需修改 vite.config.js。

### 1.2 新建目录结构

```
frontend/src/
├── components/office/
│   ├── OfficeScene.vue          # TresCanvas 根组件，场景组合
│   ├── OfficeRoom.vue           # 地板、墙壁、窗户、灯光
│   ├── OfficeDesk.vue           # 单个办公桌 + 显示器 + 椅子（复用）
│   ├── OfficeWorker.vue         # 单个工作人员（几何体占位，后续换 glTF）
│   ├── OfficeWallScreen.vue     # 墙面大屏（Canvas 纹理动态渲染）
│   └── OfficeDecorations.vue    # 绿植、咖啡机、白板、书架等
├── composables/
│   └── useWorkerAnimation.js    # 工人动画状态机
├── stores/
│   └── office.js                # 办公室场景 Pinia store
└── views/
    └── OfficeHome.vue           # 新首页（替换 Home.vue）
```

---

## Phase 2：后端 — 板块数据 API

### 2.1 新增端点

在 `d:\karensAgent\backend\routers\stock_api.py` 添加：

```python
@router.get("/sectors")
def get_sector_data():
    """返回 A 股当日板块涨跌排名，供 3D 墙面大屏使用"""
```

### 2.2 实现方案

调用 iFinD `index` MCP 工具获取申万一级行业板块数据，解析 markdown 表格为结构化 JSON。

**风险降级**：如果 iFinD 的板块查询结果不稳定，先用 `index_highfreq_quotes` 查三大指数（上证/深证/创业板）作为保底方案。

### 2.3 响应格式

```json
{
  "code": 0,
  "data": {
    "update_time": "2026-07-19 14:30:00",
    "market_status": "open",
    "sectors": [
      {"name": "半导体", "change_pct": 3.45, "rank": 1}
    ]
  }
}
```

- `market_status`: `"open"` / `"closed"` — 前端据此调整轮询频率
- 添加 30 秒内存缓存，防止多 Tab 重复调用

---

## Phase 3：3D 静态场景

### 3.1 OfficeRoom.vue — 房间结构

- 地板：14×10 浅木色平面，`[-Math.PI/2,0,0]` 旋转
- 后墙：大型浅色平面，带 2-3 个发光窗户
- 侧墙：半高（留空天花板方便俯视）
- 灯光：AmbientLight(0.5) + DirectionalLight(模拟窗外阳光) + PointLight(暖色顶灯)
- 阴影：`cast-shadow` / `receive-shadow` 开启

### 3.2 OfficeDesk.vue — 办公桌（复用两次）

- 桌面：BoxGeometry，浅木色
- 桌腿：4 根细金属柱
- 显示器：黑色扁盒 + 微弱发光的蓝色屏幕（静态，俯视角度不需要动态内容）
- 键盘：银色薄片
- 椅子：深灰色座位 + 靠背 + 金属底座圆柱

颜色方案：
- 员工1 区域（GitHub）：深色系 `#24292e`
- 员工2 区域（股票）：深蓝色系 `#1a1a2e`

### 3.3 OfficeDecorations.vue — 装饰物

- 绿植（角落）：圆柱花盆 + 绿色球体簇
- 咖啡机（靠墙）
- 白板（侧墙）
- 书架（靠墙）
- 地毯：桌子下方暖色平面

### 3.4 OfficeWallScreen.vue — 墙面大屏

- 深色金属边框（大矩形平面）
- 屏幕区域使用 **CanvasTexture** 动态渲染：
  - 暗色背景 `#0a1628`
  - 标题栏 "A股板块实时行情"
  - 板块名称 / 涨跌幅 / 领涨股 三列布局
  - A 股红色涨绿色跌配色
  - 底部状态栏（交易中/已收盘）

### 3.5 OfficeScene.vue — 场景组合根组件

```html
<TresCanvas shadows preset="realistic"
  :camera="{ position: [0, 6, 6], fov: 55 }">
  <!-- 45° 斜俯视：相机在前上方，与水平面成约 45° 角 → 等距透视感 -->
  <OrbitControls :enableDamping :minDistance="4" :maxDistance="16"
    :maxPolarAngle="Math.PI / 2.5" :target="[0, 0, -1]" />
  <OfficeRoom />
  <OfficeDecorations />
  <OfficeDesk :position="[-3, 0, -2]" />    <!-- GitHub 工位（左侧） -->
  <OfficeWorker worker-id="github" ... @click="goAgent('github')" />
  <OfficeDesk :position="[3, 0, -2]" />     <!-- 股票工位（右侧） -->
  <OfficeWorker worker-id="stock" ... @click="goAgent('stock')" />
  <OfficeWallScreen :sectors="..." :market-status="..." />
</TresCanvas>
```

---

## Phase 4：工作人员

### 4.1 几何体占位模型

```
身体：BoxGeometry [0.3, 0.4, 0.2]（躯干）
头部：SphereGeometry radius=0.12
手臂：细 BoxGeometry ×2，向前伸展（打字姿态）
腿部：细 BoxGeometry ×2，向前延伸（坐姿）
```

鼠标悬停缩放 1.05×，指针变 pointer。

### 4.2 打字动画

`useRenderLoop` 中 `sin` 振荡手臂旋转角，幅度 ±0.05，频率 4Hz。

### 4.3 走动交流动画（useWorkerAnimation.js）

状态机：`seated → standingUp → walking → gesturing → walkingBack → sittingDown → seated`

- 随机间隔 60-120 秒触发
- 每段过渡 2 秒，使用 easeInOutCubic
- 走路路径：工位 A (x=-3) ↔ 工位 B (x=3)
- 交流阶段手臂上下摆动（比划手势）

### 4.4 glTF 模型替换策略

后续只需把 `OfficeWorker.vue` 中的几何体替换为 `<GLTFModel path="/models/worker.glb" />`，prop 接口不变。

---

## Phase 5：数据集成

### 5.1 API 层

在 `d:\karensAgent\frontend\src\api\index.js` 添加：

```js
export const getSectorData = () => api.get('/stock/sectors')
```

### 5.2 Office Store

新建 `d:\karensAgent\frontend\src\stores\office.js`，沿用 Pinia options API（和 `agent.js` 一致）：

- state: `sectors`, `marketStatus`, `updateTime`, `loading`
- actions: `fetchSectors()`, `startPolling()`, `stopPolling()`

### 5.3 数据流

```
OfficeScene.onMounted
  → officeStore.startPolling()
    → 每30s: getSectorData()
      → 更新 store.sectors
        → OfficeWallScreen watch → CanvasTexture.needsUpdate → 重新渲染文字
```

---

## Phase 6：交互

- **点击工人**：`goAgent('github')` / `goAgent('stock')` → `router.push('/agent/xxx')`
- **OrbitControls**：左键轨道旋转、滚轮缩放、右键平移
- **悬浮效果**：`@pointer-enter` 放大 1.05× + pointer 光标

---

## Phase 7：替换 Home.vue

### 7.1 新建 OfficeHome.vue

```vue
<template>
  <div class="office-home">
    <Suspense>
      <OfficeScene />
      <template #fallback>
        <div class="loading-fallback"><div class="spinner" /><p>加载 3D 场景中...</p></div>
      </template>
    </Suspense>
  </div>
</template>
```

CSS：`position: fixed; inset: 0; top: var(--topnav-height, 64px)`

### 7.2 修改路由

`d:\karensAgent\frontend\src\router\index.js` 第 7 行：

```diff
- component: () => import('../views/Home.vue'),
+ component: () => import('../views/OfficeHome.vue'),
```

旧 `Home.vue` 保留为备份。TopNav 的 `goHome()` 无需改动。

### 7.3 删除/归档

`style.css` 中仅 Home.vue 使用的全局样式类（`.agent-card-grid` 等）暂不删除，等 3D 场景稳定上线后再清理。

---

## 实施顺序

| 顺序 | Phase | 可独立验证 |
|------|-------|-----------|
| 1 | Phase 1 — 安装依赖 | `npm ls three @tresjs/core @tresjs/cientos` |
| 2 | Phase 2 — 后端 API | `curl localhost:8900/api/stock/sectors` |
| 3 | Phase 3 — 静态场景 | 浏览器看到空办公室 |
| 4 | Phase 4 — 工人 | 看到两个小人+打字动画 |
| 5 | Phase 5 — 数据联动 | 墙面大屏显示板块数据 |
| 6 | Phase 6 — 交互 | 点击跳转+轨道控制 |
| 7 | Phase 7 — 路由切换 | `/` 显示 3D 场景，不显示卡片 |

---

## 验证清单

- [ ] `npm run build` 无报错
- [ ] 浏览器访问 `http://localhost:5173/#/` 看到 3D 办公室
- [ ] 摄像机初始角度为 45° 斜俯视，两工位和墙面大屏均可见
- [ ] 鼠标可旋转/缩放/平移
- [ ] 两个工人坐在各自工位，手臂轻微抖动（打字）
- [ ] 每隔 60-120 秒工人自动走到对方工位交流
- [ ] 墙面大屏显示板块数据（交易时段）或"已收盘"（非交易时段）
- [ ] 点击工人跳转到对应 Agent 子页面
- [ ] TopNav 各标签和 logo 点击正常
- [ ] /agent/github、/agent/stock 等现有页面无回归
- [ ] 60fps 稳定运行（DevTools FPS 检查）
