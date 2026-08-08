# 3D 模型素材目录

本目录存放 3D 办公室场景的外部 glTF 素材。几何体兜底仍在组件内，
模型缺失时场景自动降级为原积木风，**素材可随时增量添加**。

> 工作人员已改为纯代码构建，无外部人物模型；人物模块位于
> `frontend/src/three/character/`，如需调整造型/动画请改代码而非换模型。

## 目录约定

```
models/
├── furniture/   办公家具（桌 / 椅 / 显示器 …）
├── decor/       装饰物（绿植 / 书架 / 咖啡机 …）
└── textures/    PBR 贴图（地板 / 墙面，JPG 格式）
```

## 选货指南

### 推荐站点（均为 CC0：免署名、可商用、免费下载）

| 站点 | 地址 | 适合选 | 搜索关键词 |
|---|---|---|---|
| Poly Pizza | https://poly.pizza | 家具 / 装饰（量最大） | `office desk`、`office chair`、`computer monitor`、`potted plant`、`bookshelf`、`coffee machine` |
| Kenney | https://kenney.nl/assets | 风格统一的整套资产 | `Office Pack`、`City Kit` |
| ambientCG | https://ambientcg.com | PBR 贴图（放 textures/） | `Wood Flooring`、`Painted Wall`，下 JPG 1K/2K |

> 国内访问 Poly Pizza / Quaternius 若打不开，挂代理即可。

### 三条硬标准

1. **格式**：`.glb`（二进制 glTF，单文件内嵌贴图；下载页一般可选 glTF/GLB）
2. **许可**：`CC0`（上述站点默认即是；Sketchfab 需手动筛选，慎用）
3. **风格**：低多边形 low-poly（与现有积木风协调，且文件小加载快）

### 各槽位尺寸参考（真实世界米制，仅供选货时目测比例）

| 槽位 | 建议文件名 | 现有几何体尺寸参考 |
|---|---|---|
| 办公桌 | `desk.glb` | 桌面 1.7 × 0.85m，桌面高 0.75m |
| 办公椅 | `chair.glb` | 座垫高 0.46m，靠背顶高 0.97m |
| 显示器 | `monitor.glb` | 屏宽 0.72m，屏幕中心高 1.18m |
| 绿植 | `plant.glb` | 全高约 1.3m |
| 书架 | `bookshelf.glb` | 1.2 × 1.8 × 0.35m |
| 咖啡机 | `coffee_machine.glb` | 0.5 × 1.0 × 0.5m |

**文件名用小写蛇形**（如 `office_chair.glb`）。尺寸不必精确——
接入代码会自动缩放并把模型底部对齐地面。

## 接入流程

1. 下载 glb → 放进对应子目录 → 按上表命名
2. 告诉开发（Claude）文件名与想替换的场景部件
3. 接入后浏览器验收：360° 环绕 / 阴影 / 工位点击交互
