<script setup>
import { ref, onMounted } from 'vue'
import { useStockStore } from '../../stores/stock.js'

const store = useStockStore()

/* ═══════════════════════════════════════════
 * 添加面板
 * ═══════════════════════════════════════════ */
const newCode = ref('')
const newName = ref('')
const newNotes = ref('')
const showAddPanel = ref(false)

/* ═══════════════════════════════════════════
 * 行内编辑
 * ═══════════════════════════════════════════ */
const editingCode = ref('')
const editNotes = ref('')
const editEnabled = ref(true)

/* ═══════════════════════════════════════════
 * 系统配置（localStorage 持久化）
 * ═══════════════════════════════════════════ */
const feishuAutoPush = ref(false)
/* 10 维度与 report.py DIMENSIONS 严格对齐 */
const dimensions = ref([
  { key: 'quotes',       label: '实时行情',        checked: true },
  { key: 'summary',      label: '基本信息与估值',   checked: true },
  { key: 'performance',  label: '近期行情走势',     checked: true },
  { key: 'financials',   label: '财务数据',         checked: true },
  { key: 'shareholders', label: '股东结构',         checked: true },
  { key: 'risk',         label: '风险评估',         checked: true },
  { key: 'esg',          label: 'ESG 评级',         checked: true },
  { key: 'events',       label: '重大事件',         checked: true },
  { key: 'news',         label: '近期新闻',         checked: true },
  { key: 'notices',      label: '公司公告',         checked: true },
])

/* iFind 连接状态: checking | connected | error */
const ifindStatus = ref('checking')
const todayStr = ref('')

/* ═══════════════════════════════════════════
 * 初始化
 * ═══════════════════════════════════════════ */
onMounted(async () => {
  /* 日期 */
  const d = new Date()
  todayStr.value = d.getFullYear() + '-'
    + String(d.getMonth() + 1).padStart(2, '0') + '-'
    + String(d.getDate()).padStart(2, '0')

  /* 自选股 */
  store.fetchWatchlist()

  /* 恢复飞书推送配置 */
  try {
    const v = localStorage.getItem('stock_settings_feishu_push')
    if (v !== null) feishuAutoPush.value = v === 'true'
  } catch (_) {}

  /* 恢复分析维度配置 */
  try {
    const v = localStorage.getItem('stock_settings_dimensions')
    if (v) {
      const keys = JSON.parse(v)
      dimensions.value.forEach(d => { d.checked = keys.includes(d.key) })
    }
  } catch (_) {}

  /* 检测 iFind / 后端连通性 */
  try {
    const res = await fetch('/api/health')
    const data = await res.json()
    ifindStatus.value = data.ifind ? 'connected' : 'error'
  } catch (_) {
    ifindStatus.value = 'error'
  }
})

/* ═══════════════════════════════════════════
 * 配置持久化
 * ═══════════════════════════════════════════ */
function saveFeishuConfig() {
  try { localStorage.setItem('stock_settings_feishu_push', String(feishuAutoPush.value)) } catch (_) {}
}

function saveDimensionConfig() {
  try {
    const keys = dimensions.value.filter(d => d.checked).map(d => d.key)
    localStorage.setItem('stock_settings_dimensions', JSON.stringify(keys))
  } catch (_) {}
}

/* ═══════════════════════════════════════════
 * 添加自选股
 * ═══════════════════════════════════════════ */
function toggleAddPanel() {
  showAddPanel.value = !showAddPanel.value
  if (!showAddPanel.value) {
    newCode.value = ''
    newName.value = ''
    newNotes.value = ''
  }
}

async function handleAdd() {
  const code = newCode.value.trim()
  if (!code) { store.showToast('请输入股票代码'); return }
  const res = await store.addWatchlist({
    stock_code: code,
    stock_name: newName.value.trim(),
    notes: newNotes.value.trim(),
  })
  if (res && res.code === 0) {
    showAddPanel.value = false
    newCode.value = ''
    newName.value = ''
    newNotes.value = ''
  }
}

/* ═══════════════════════════════════════════
 * 删除
 * ═══════════════════════════════════════════ */
async function handleDelete(item) {
  if (!confirm(`确认将 ${item.stock_name}（${item.stock_code}）移出自选？`)) return
  await store.deleteWatchlist(item.stock_code)
}

/* ═══════════════════════════════════════════
 * 快速切换启用 / 停用
 * ═══════════════════════════════════════════ */
async function toggleEnabled(item) {
  const next = item.enabled ? 0 : 1  // 快照当前值，避免快速双击读到旧值
  await store.updateWatchlist(item.stock_code, { enabled: next })
}

/* ═══════════════════════════════════════════
 * 行内编辑
 * ═══════════════════════════════════════════ */
function startEdit(item) {
  editingCode.value = item.stock_code
  editNotes.value = item.notes || ''
  editEnabled.value = item.enabled !== 0
}

async function saveEdit(code) {
  await store.updateWatchlist(code, {
    notes: editNotes.value,
    enabled: editEnabled.value ? 1 : 0,
  })
  editingCode.value = ''
}

function cancelEdit() {
  editingCode.value = ''
}
</script>

<template>
  <div class="settings-page">
    <!-- ═══════════════════════════════════════
         页面头版
         ═══════════════════════════════════════ -->
    <div class="masthead">
      <div class="issue-tag">CONFIG · {{ todayStr }}</div>
      <h1>配置管理</h1>
      <p>自选股管理与系统偏好设置</p>
    </div>

    <!-- ═══════════════════════════════════════
         自选股管理
         ═══════════════════════════════════════ -->
    <div class="section-header">
      <h2>⭐ 自选股管理</h2>
      <button class="btn btn-outline btn-sm" @click="toggleAddPanel">
        {{ showAddPanel ? '收起' : '+ 添加自选' }}
      </button>
    </div>

    <!-- 添加面板 -->
    <div v-if="showAddPanel" class="add-panel">
      <h3>添加自选股</h3>
      <div class="add-form">
        <div class="form-group">
          <label>股票代码</label>
          <input
            v-model="newCode"
            class="form-input"
            type="text"
            placeholder="例: 600519"
            @keyup.enter="handleAdd"
          />
        </div>
        <div class="form-group">
          <label>股票名称</label>
          <input
            v-model="newName"
            class="form-input wide"
            type="text"
            placeholder="例: 贵州茅台"
            @keyup.enter="handleAdd"
          />
        </div>
        <div class="form-group">
          <label>备注</label>
          <input
            v-model="newNotes"
            class="form-input wide"
            type="text"
            placeholder="选填"
            @keyup.enter="handleAdd"
          />
        </div>
        <button class="btn btn-primary btn-sm" @click="handleAdd">确认添加</button>
        <button class="btn btn-outline btn-sm" @click="toggleAddPanel">取消</button>
      </div>
    </div>

    <!-- 自选股表格 -->
    <div class="watchlist-table">
      <!-- 表头 -->
      <div class="watchlist-row header-row">
        <div class="watchlist-col-header">代码</div>
        <div class="watchlist-col-header">名称 / 备注</div>
        <div class="watchlist-col-header">备注</div>
        <div class="watchlist-col-header">状态</div>
        <div class="watchlist-col-header">操作</div>
      </div>

      <!-- 空状态 -->
      <div v-if="store.watchlist.length === 0" class="empty-state">
        <h4>暂无自选股</h4>
        <p>点击上方"+ 添加自选"开始添加关注的股票</p>
      </div>

      <!-- 数据行 -->
      <div
        v-for="item in store.watchlist"
        :key="item.stock_code"
        class="watchlist-row"
      >
        <!-- 代码 -->
        <div class="stock-code">{{ item.stock_code }}</div>

        <!-- 名称 -->
        <div class="stock-name">{{ item.stock_name }}</div>

        <!-- 备注 -->
        <div class="stock-note" :title="item.notes || ''">
          <template v-if="editingCode === item.stock_code">
            <input
              v-model="editNotes"
              class="form-input edit-inline"
              @keyup.enter="saveEdit(item.stock_code)"
              @keyup.escape="cancelEdit"
            />
          </template>
          <span v-else>{{ item.notes || '—' }}</span>
        </div>

        <!-- 状态 -->
        <div>
          <template v-if="editingCode === item.stock_code">
            <label class="checkbox-label">
              <input type="checkbox" v-model="editEnabled" />
              {{ editEnabled ? '启用' : '停用' }}
            </label>
          </template>
          <span
            v-else
            :class="['status-tag', item.enabled ? 'enabled' : 'disabled']"
          >
            {{ item.enabled ? '启用' : '停用' }}
          </span>
        </div>

        <!-- 操作 -->
        <div class="row-actions">
          <template v-if="editingCode === item.stock_code">
            <button class="btn btn-outline btn-sm" @click="saveEdit(item.stock_code)">保存</button>
            <button class="btn btn-danger btn-sm" @click="cancelEdit">取消</button>
          </template>
          <template v-else>
            <button class="btn btn-outline btn-sm" @click="startEdit(item)" title="编辑">✎</button>
            <button
              class="btn btn-outline btn-sm"
              @click="toggleEnabled(item)"
              :title="item.enabled ? '停用' : '启用'"
            >{{ item.enabled ? '⊘' : '✓' }}</button>
            <button class="btn btn-danger btn-sm" @click="handleDelete(item)" title="删除">✕</button>
          </template>
        </div>
      </div>
    </div>

    <!-- ═══════════════════════════════════════
         分隔
         ═══════════════════════════════════════ -->
    <hr class="section-divider" />

    <!-- ═══════════════════════════════════════
         系统配置
         ═══════════════════════════════════════ -->
    <div class="config-section">
      <h2>⚙ 系统配置</h2>

      <!-- 飞书推送 -->
      <div class="config-item">
        <div class="config-left">
          <div class="config-label">自动推送飞书</div>
          <div class="config-desc">分析完成后自动将综合报告推送到绑定的飞书群聊，无需手动操作。</div>
        </div>
        <label class="toggle-switch">
          <input type="checkbox" v-model="feishuAutoPush" @change="saveFeishuConfig" />
          <span class="toggle-slider"></span>
        </label>
      </div>

      <!-- 默认分析维度 -->
      <div class="config-item config-item-stack">
        <div class="config-left config-left-full">
          <div class="config-label">默认分析维度</div>
          <div class="config-desc">选择分析时默认采集的数据维度，可随时在仪表盘按需调整。</div>
        </div>
        <div class="checkbox-group" @change="saveDimensionConfig">
          <label
            v-for="dim in dimensions"
            :key="dim.key"
            class="checkbox-item"
            :class="{ checked: dim.checked }"
          >
            <input type="checkbox" :value="dim.key" v-model="dim.checked" />
            {{ dim.label }}
          </label>
        </div>
      </div>

      <!-- iFind 连接状态 -->
      <div class="config-item">
        <div class="config-left">
          <div class="config-label">iFind 连接状态</div>
          <div class="config-desc">同花顺 iFind MCP 数据源连接状况，系统启动时自动检测。</div>
        </div>
        <div class="status-indicator">
          <template v-if="ifindStatus === 'checking'">
            <span class="status-dot unknown"></span>
            <span style="color:var(--ink-tertiary, #9a948d)">检测中…</span>
          </template>
          <template v-else-if="ifindStatus === 'connected'">
            <span class="status-dot connected"></span>
            <span style="color:var(--green, #166534)">已连接</span>
          </template>
          <template v-else>
            <span class="status-dot error"></span>
            <span style="color:var(--red, #991b1b)">未连接</span>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ═══════════════════════════════════════════
   设计 Token — 精密纸媒交易台
   ═══════════════════════════════════════════ */
.settings-page {
  --paper-bg:       #ffffff;
  --paper-card:     #ffffff;
  --paper-muted:    #f5f5f4;
  --ink-primary:    #1a1816;
  --ink-secondary:  #6b6560;
  --ink-tertiary:   #9a948d;
  --ink-disabled:   #c4beb6;
  --accent:         #b45309;
  --accent-hover:   #92400e;
  --accent-soft:    #fef3c7;
  --accent-ink:     #78350f;
  --green:          #166534;
  --green-soft:     #dcfce7;
  --red:            #991b1b;
  --red-soft:       #fee2e2;
  --border:         #e5e5e5;
  --border-light:   #e8e8e8;
  --shadow-sm:      0 1px 2px rgba(26,24,22,0.04);
  --shadow-md:      0 4px 12px rgba(26,24,22,0.06);
  --shadow-btn:     inset 0 1px 0 rgba(255,255,255,0.25), 0 1px 2px rgba(26,24,22,0.08);
  --shadow-btn-active: inset 0 1px 2px rgba(26,24,22,0.15);
  --radius-sm:      3px;
  --radius-md:      5px;
  --radius-lg:      8px;
  --font-display:   'Bricolage Grotesque', 'Noto Sans SC', 'PingFang SC', sans-serif;
  --font-serif:     'Noto Serif SC', 'STSong', 'SimSun', serif;
  --font-mono:      'JetBrains Mono', 'SF Mono', 'Cascadia Code', monospace;
  --ease-out:       cubic-bezier(0.16, 1, 0.3, 1);

  position: relative;
  z-index: 1;
  max-width: 1400px;
  margin: 0 auto;
  padding: 32px 40px 60px;
  font-family: var(--font-display);
  color: var(--ink-primary);
  line-height: 1.55;
}

/* ═══════════════════════════════════════════
   头版
   ═══════════════════════════════════════════ */
.masthead {
  padding-bottom: 28px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 28px;
}
.issue-tag {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  background: var(--ink-primary);
  color: var(--paper-card);
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  margin-bottom: 12px;
  letter-spacing: 0.08em;
}
.masthead h1 {
  font-family: var(--font-serif);
  font-size: 2.6rem;
  font-weight: 900;
  letter-spacing: -0.03em;
  line-height: 1.1;
  margin-bottom: 8px;
}
.masthead p {
  color: var(--ink-secondary);
  font-size: 0.9rem;
  font-weight: 500;
  letter-spacing: 0.02em;
}

/* ═══════════════════════════════════════════
   按钮
   ═══════════════════════════════════════════ */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: var(--radius-sm);
  font-family: var(--font-display);
  font-size: 0.85rem;
  font-weight: 600;
  border: 1px solid transparent;
  cursor: pointer;
  transition: all .12s ease;
}
.btn-primary {
  background: var(--accent);
  color: #fff;
  box-shadow: var(--shadow-btn);
}
.btn-primary:hover {
  background: var(--accent-hover);
  transform: translateY(-1px);
}
.btn-primary:active {
  transform: translateY(0);
  box-shadow: var(--shadow-btn-active);
}
.btn-outline {
  background: var(--paper-card);
  color: var(--ink-primary);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-btn);
}
.btn-outline:hover {
  background: var(--paper-muted);
}
.btn-sm {
  padding: 5px 14px;
  font-size: 0.78rem;
}
.btn-danger {
  background: transparent;
  color: var(--red);
  border: 1px solid var(--border);
}
.btn-danger:hover {
  background: var(--red-soft);
  border-color: var(--red);
}

/* ═══════════════════════════════════════════
   区块标题
   ═══════════════════════════════════════════ */
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}
.section-header h2 {
  font-family: var(--font-serif);
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--ink-primary);
}

/* ═══════════════════════════════════════════
   添加面板
   ═══════════════════════════════════════════ */
.add-panel {
  margin-bottom: 28px;
  padding: 28px 0;
  border-bottom: 1px solid var(--border-light);
}
.add-panel h3 {
  font-family: var(--font-serif);
  font-size: 1.05rem;
  font-weight: 700;
  margin-bottom: 20px;
  color: var(--ink-primary);
}
.add-form {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  flex-wrap: wrap;
}
.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.form-group label {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--ink-tertiary);
}
.form-input {
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  font-size: 0.85rem;
  font-family: var(--font-mono);
  color: var(--ink-primary);
  background: var(--paper-card);
  outline: none;
  transition: border-color .15s ease, box-shadow .15s ease;
}
.form-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(180,83,9,0.08);
}
.form-input::placeholder {
  color: var(--ink-tertiary);
}
.form-input.wide {
  min-width: 220px;
}
.form-input.edit-inline {
  width: 100%;
  padding: 4px 8px;
  font-size: 0.8rem;
}

/* ═══════════════════════════════════════════
   自选股表格 — 纸媒网格行
   ═══════════════════════════════════════════ */
.watchlist-table {
  border-top: 1px solid var(--border);
  margin-bottom: 72px;
}
.watchlist-row {
  display: grid;
  grid-template-columns: 120px 1fr 140px 80px 100px;
  gap: 24px;
  align-items: center;
  padding: 16px 0;
  border-bottom: 1px solid var(--border-light);
  transition: background .15s ease;
}
.watchlist-row:hover {
  background: var(--paper-muted);
  margin: 0 -12px;
  padding: 16px 12px;
  border-radius: var(--radius-sm);
}
.watchlist-row.header-row {
  padding: 10px 0;
  border-bottom: 1px solid var(--ink-primary);
}
.watchlist-row.header-row:hover {
  background: none;
  margin: 0;
  padding: 10px 0;
  border-radius: 0;
}
.watchlist-col-header {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--ink-tertiary);
}

/* 单元格内容 */
.stock-code {
  font-family: var(--font-mono);
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--ink-primary);
  letter-spacing: 0.04em;
}
.stock-name {
  font-family: var(--font-serif);
  font-size: 1rem;
  font-weight: 600;
  color: var(--ink-primary);
}
.stock-note {
  font-size: 0.82rem;
  color: var(--ink-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 状态标签 */
.status-tag {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 3px 10px;
  border-radius: var(--radius-sm);
}
.status-tag.enabled {
  background: var(--green-soft);
  color: var(--green);
}
.status-tag.disabled {
  background: var(--paper-muted);
  color: var(--ink-tertiary);
}

/* 编辑模式 checkbox */
.checkbox-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  cursor: pointer;
  white-space: nowrap;
}
.checkbox-label input[type="checkbox"] {
  accent-color: var(--accent);
  width: 14px;
  height: 14px;
}

/* 操作按钮 */
.row-actions {
  display: flex;
  gap: 6px;
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 72px 0;
  border-bottom: 1px solid var(--border-light);
}
.empty-state h4 {
  font-family: var(--font-serif);
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--ink-secondary);
  margin-bottom: 6px;
}
.empty-state p {
  font-size: 0.85rem;
  color: var(--ink-tertiary);
}

/* ═══════════════════════════════════════════
   分隔线
   ═══════════════════════════════════════════ */
.section-divider {
  border: none;
  border-top: 1px solid var(--border);
  margin: 72px 0;
}

/* ═══════════════════════════════════════════
   系统配置
   ═══════════════════════════════════════════ */
.config-section {
  margin-bottom: 56px;
}
.config-section h2 {
  font-family: var(--font-serif);
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 28px;
}

/* 配置项 */
.config-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 0;
  border-bottom: 1px solid var(--border-light);
}
.config-item:first-of-type {
  border-top: 1px solid var(--border-light);
}
.config-left {
  max-width: 520px;
  flex: 1;
  padding-right: 24px;
}
/* 维度配置项：上下堆叠，描述与 checkbox 各占一行 */
.config-item-stack {
  flex-direction: column;
  align-items: flex-start;
  gap: 14px;
}
.config-left-full {
  max-width: none;
  padding-right: 0;
}
.config-label {
  font-family: var(--font-serif);
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--ink-primary);
  margin-bottom: 4px;
}
.config-desc {
  font-size: 0.8rem;
  color: var(--ink-tertiary);
  line-height: 1.5;
}

/* Toggle 开关 */
.toggle-switch {
  position: relative;
  width: 44px;
  height: 26px;
  flex-shrink: 0;
}
.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}
.toggle-slider {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: var(--border-light);
  border-radius: 26px;
  cursor: pointer;
  transition: background .2s ease;
}
.toggle-slider::before {
  content: '';
  position: absolute;
  top: 3px;
  left: 3px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.12);
  transition: transform .2s var(--ease-out);
}
.toggle-switch input:checked + .toggle-slider {
  background: var(--green);
}
.toggle-switch input:checked + .toggle-slider::before {
  transform: translateX(18px);
}

/* 维度多选 */
.checkbox-group {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}
.checkbox-item {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 0.85rem;
  color: var(--ink-secondary);
  cursor: pointer;
  padding: 6px 12px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  transition: all .15s ease;
}
.checkbox-item:hover {
  border-color: var(--border);
}
.checkbox-item input[type="checkbox"] {
  accent-color: var(--accent);
  width: 15px;
  height: 15px;
}
.checkbox-item.checked {
  border-color: var(--accent);
  background: var(--accent-soft);
  color: var(--accent-ink);
}

/* iFind 连接状态 */
.status-indicator {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-mono);
  font-size: 0.78rem;
  flex-shrink: 0;
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.status-dot.connected {
  background: var(--green);
  box-shadow: 0 0 6px rgba(22,101,52,0.3);
}
.status-dot.unknown {
  background: var(--ink-tertiary);
}
.status-dot.error {
  background: var(--red);
  box-shadow: 0 0 6px rgba(153,27,27,0.3);
}

/* ═══════════════════════════════════════════
   响应式
   ═══════════════════════════════════════════ */
@media (max-width: 820px) {
  .settings-page {
    padding: 20px;
  }
  .watchlist-row {
    grid-template-columns: 1fr;
    gap: 6px;
    padding: 20px 0;
  }
  .watchlist-row.header-row {
    display: none;
  }
  .watchlist-row:hover {
    margin: 0;
    padding: 20px 0;
  }
  .add-form {
    flex-direction: column;
    align-items: stretch;
  }
  .form-input.wide {
    min-width: auto;
  }
  .checkbox-group {
    flex-direction: column;
  }
  .config-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  .config-left {
    padding-right: 0;
  }
}
</style>
