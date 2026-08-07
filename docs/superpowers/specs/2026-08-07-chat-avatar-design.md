# 问答助理头像与名称时间设计

日期：2026-08-07
状态：已批准，待实施

## 背景

问答助理面板（投研报告页右列「karens 问答助理」）当前消息只有气泡，
没有头像、名称、时间，不像主流聊天软件（微信/QQ）的对话形态。
需求：双方消息带头像，头像旁显示名称与对话时间，微信式镜像布局。

## 已确认的需求决策（王磊哥哥拍板）

1. 布局：微信式镜像 —— 助理头像在左、名称时间在头像右上方；
   用户头像在右、时间在头像左上方
2. 头像来源：项目内置本地图（双方都是），**不做上传功能**；
   占底图可同名替换
3. 名称：助理侧显示「karens」；用户侧**不显示名称**，只显示时间
4. 时间格式：今天的消息显示「时:分」；其他日子只显示「月-日」

## 组件与数据流

### 单条消息组件（新增 ChatMessageItem.vue）

- props：message（role/content/tool_calls/created_at）
- 一条消息 = 头像 + 元信息行（名称·时间）+ 气泡 + 步骤卡片（助理且有工具调用时）
- 左右镜像由组件内 class 处理（role=user 时右对齐）
- 元信息行：助理侧「karens · 时间」；用户侧仅「时间」
- created_at 缺失时不渲染时间，页面不崩

### 问答面板（改造 AiChatPanel.vue）

- 消息循环改用 ChatMessageItem，删除旧 .msg/.bubble 结构与样式
- 其余（思考中占位、实时步骤卡片、输入区）不动

### 状态仓库（stock.js）

- askChat 推送 user/assistant 消息时补 `created_at`（前端发送时刻 ISO 串）
- 历史消息沿用后端 ChatMessage.created_at（list_messages 已返回）

### 头像资源（新增）

- frontend/src/assets/chat/assistant.svg — 浅色简约机器人
- frontend/src/assets/chat/user.svg — 浅色简约人像
- 组件内 import 引用；用户有偏好直接同名替换文件

### 时间格式化（新增 utils/time.js）

- formatChatTime(iso)：今天 → "HH:mm"；其他 → "MM-DD"
- 非法/空值 → 返回空串，调用方据此不渲染时间行内容

## 改动清单

| 文件 | 改动 |
|---|---|
| frontend/src/components/report/ChatMessageItem.vue | 新增 |
| frontend/src/components/report/AiChatPanel.vue | 换用新组件、删旧样式 |
| frontend/src/stores/stock.js | askChat 补 created_at |
| frontend/src/utils/time.js | 新增 formatChatTime |
| frontend/src/assets/chat/{assistant,user}.svg | 新增 |
| frontend/src/utils/time.test.js | 新增测试 |

## 测试用例

1. formatChatTime：今天 → 时:分；昨天/更早 → 月-日；空/非法 → 空串
2. 历史消息（带 created_at）渲染名称时间行正确
3. 实时消息（前端补 created_at）渲染正确
4. 旧数据无 created_at → 不显示时间，不崩
5. 助理侧显示「karens · 时间」，用户侧仅时间
6. 窄屏镜像布局气泡不溢出、元信息行不折行错乱（人工目检）

## 不做的事

- 头像上传/浏览器存储/后端上传接口（已砍）
- 用户侧名称显示（已砍）
- 历史数据时间回填
