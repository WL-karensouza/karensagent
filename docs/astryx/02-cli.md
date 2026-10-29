# 02 · CLI 命令与模板使用流程

> 所有命令写成 `npx @astryxdesign/cli@0.7.4 <cmd>` 是官方建议的锁定写法。
> 项目内装了包时，`npx @astryxdesign/cli <cmd>` 即可。

---

## 命令全表

| 命令 | 作用 |
|---|---|
| `template --list` | 列出全部页面模板 + 区块模板及 slug |
| `template <slug> <目录>` | 把模板源码生成到指定目录 |
| `component` | 列出全部组件（含每个组件的 import 模块） |
| `component <Name>` | 查某个组件的 props、用法、主题、**准确 Import 行** |
| `search "<关键词>"` | 跨组件/文档/模板/区块搜索 |
| `build "<想法>"` | 告诉你该用哪个模板、还缺哪些区块 |
| `docs` | 列出全部文档主题 |
| `docs tokens` | 设计 token 总览 |
| `docs tokens/tokens-color` | 颜色 token 全表 |
| `docs use-a-theme` | 主题完整指南 |
| `docs migration/migration-setup` | 层叠样式（cascade layer）接入，**建页面前必读** |
| `theme list` / `theme add <slug>` / `theme eject <slug>` | 查 / 加 / 分叉主题 |
| `init [--all]` | 生成 AI 编码文档（非交互） |
| `swizzle <Component>` | 把组件源码复制到本地，可改 |
| `doctor` | 环境体检，升级前跑 |
| `help` | 列出所有命令 |

---

## 模板使用：四步流程

```
1. 查 —— template --list，找到目标模板 slug
2. 生 —— template <slug> ./app/<页面名>
3. 读 —— component <Name> 查生成代码里用到的组件 props
4. 改 —— 只改业务内容，尽量不动布局骨架
```

**第 4 步是重点**：Astryx 官方 AI 文档原话是「keep its frame, gap and padding; replace the content」。
动了骨架，就等于放弃后续升级。

---

## 需要注意的两个真实成本

### 1. 模板会带额外依赖

例如 `ai-chat-landing` 模板生成后提示：

```
Install missing dependencies: npm install @heroicons/react@"^2.2.0"
```

**生成完立刻看终端最后几行**，有没有这条。不需要模板里那些图标的话，直接改写掉相关代码，比装依赖干净。

### 2. 模板文件很大

`ai-chat-landing/page.tsx` **478 行**，包含分类切换、模式选择、@ 提及、语音输入、附件抽屉等大量功能。
如果只想要「标题 + 输入框 + 推荐卡片」，**照它的骨架重写一个 90 行的组件**比删改它更快、更省心。

实测可行的最小骨架（Astryx + 无额外依赖）：

```tsx
<Layout
  height="fill"
  contentWidth={720}
  padding={6}
  content={
    <LayoutContent>
      <VStack gap={8} vAlign="center" style={{ minHeight: '100%' }}>
        <Text type="display-2" as="h1">标题</Text>
        <ChatComposer
          onSubmit={handleAsk}
          placeholder="问点什么…"
          input={<ChatComposerInput placeholder="问点什么…" />}
        />
        <Grid columns={{ minWidth: 280 }} gap={3}>
          <ClickableCard label="卡片" variant="muted" padding={3} onClick={...}>
            <VStack gap={0.5}>
              <Heading level={4}>标题</Heading>
              <Text type="body" color="secondary" size="xsm">说明</Text>
            </VStack>
          </ClickableCard>
        </Grid>
      </VStack>
    </LayoutContent>
  }
/>
```

---

## 全局安装（可选）

```bash
npm install -g @astryxdesign/cli
```

之后任意目录可用 `astryx ...`。
**但全局安装不会改变项目内使用的版本**——团队和 CI 仍以项目依赖为准，全局只当快捷方式。
