<script setup>
import { ref, onMounted } from 'vue'
import { useStockStore } from '../../stores/stock.js'

const store = useStockStore()

/* 添加表单 */
const newCode = ref('')
const newName = ref('')
const newNotes = ref('')

/* 编辑状态 */
const editingCode = ref('')
const editNotes = ref('')
const editEnabled = ref(true)

/* 技能列表（静态展示） */
const skills = [
  { name: 'technical', display: '技术面', desc: 'K线形态、均线、MACD/RSI 指标' },
  { name: 'capital', display: '资金面', desc: '主力资金、融资融券、量价配合' },
  { name: 'news', display: '消息面', desc: '新闻关键词、利好/利空分类' },
  { name: 'fundamental', display: '基本面', desc: 'PE/PB 估值、ROE、营收增速' },
  { name: 'risk', display: '风险面', desc: '四维度风险信号 + 等级评定' },
  { name: 'market_env', display: '市场环境', desc: '市值风格、板块关联' },
]

onMounted(() => {
  store.fetchWatchlist()
})

async function handleAdd() {
  const code = newCode.value.trim()
  if (!code) {
    store.showToast('请输入股票代码')
    return
  }
  const res = await store.addWatchlist({
    stock_code: code,
    stock_name: newName.value.trim(),
    notes: newNotes.value.trim(),
  })
  if (res && res.code === 0) {
    newCode.value = ''
    newName.value = ''
    newNotes.value = ''
  }
}

async function handleDelete(code) {
  await store.deleteWatchlist(code)
}

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
  <div>
    <div class="page-header">
      <h1>配置管理</h1>
      <p>管理自选股列表与分析技能</p>
    </div>

    <!-- 自选股管理 -->
    <div class="card" style="margin-bottom:24px;">
      <h3 style="margin-bottom:16px;font-size:1rem;">⭐ 自选股管理</h3>

      <!-- 添加表单 -->
      <div style="display:flex;gap:12px;align-items:flex-end;flex-wrap:wrap;margin-bottom:20px;">
        <div class="form-group" style="margin-bottom:0;flex:1;min-width:120px;">
          <label class="form-label">股票代码 *</label>
          <input
            v-model="newCode"
            class="form-input"
            placeholder="如 600519"
            @keyup.enter="handleAdd"
          />
        </div>
        <div class="form-group" style="margin-bottom:0;flex:1;min-width:120px;">
          <label class="form-label">股票名称</label>
          <input
            v-model="newName"
            class="form-input"
            placeholder="如 贵州茅台"
            @keyup.enter="handleAdd"
          />
        </div>
        <div class="form-group" style="margin-bottom:0;flex:2;min-width:160px;">
          <label class="form-label">备注</label>
          <input
            v-model="newNotes"
            class="form-input"
            placeholder="可选备注"
            @keyup.enter="handleAdd"
          />
        </div>
        <button class="btn btn-primary" @click="handleAdd">添加</button>
      </div>

      <!-- 自选股列表 -->
      <div v-if="store.watchlist.length === 0" class="empty-state" style="padding:30px;">
        <p>暂无自选股，请添加</p>
      </div>
      <table v-else class="data-table">
        <thead>
          <tr>
            <th>代码</th>
            <th>名称</th>
            <th>备注</th>
            <th>状态</th>
            <th>添加时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in store.watchlist" :key="item.stock_code">
            <td style="font-weight:600;">{{ item.stock_code }}</td>
            <td>{{ item.stock_name }}</td>
            <td style="max-width:200px;">
              <template v-if="editingCode === item.stock_code">
                <input
                  v-model="editNotes"
                  class="form-input"
                  style="padding:4px 8px;font-size:0.85rem;"
                  @keyup.enter="saveEdit(item.stock_code)"
                  @keyup.escape="cancelEdit"
                />
              </template>
              <template v-else>
                <span style="color:var(--text-secondary);font-size:0.85rem;">{{ item.notes || '—' }}</span>
              </template>
            </td>
            <td>
              <template v-if="editingCode === item.stock_code">
                <label style="display:flex;align-items:center;gap:6px;cursor:pointer;font-size:0.85rem;">
                  <input type="checkbox" v-model="editEnabled" />
                  {{ editEnabled ? '启用' : '禁用' }}
                </label>
              </template>
              <template v-else>
                <span :class="item.enabled ? 'tag active' : 'tag'" style="font-size:0.75rem;">
                  {{ item.enabled ? '启用' : '禁用' }}
                </span>
              </template>
            </td>
            <td style="color:var(--text-muted);font-size:0.8rem;">{{ item.added_at?.slice(0, 10) }}</td>
            <td>
              <div style="display:flex;gap:6px;">
                <template v-if="editingCode === item.stock_code">
                  <button class="btn btn-primary btn-sm" @click="saveEdit(item.stock_code)">保存</button>
                  <button class="btn btn-outline btn-sm" @click="cancelEdit">取消</button>
                </template>
                <template v-else>
                  <button class="btn btn-outline btn-sm" @click="startEdit(item)">编辑</button>
                  <button class="btn btn-outline btn-sm" @click="handleDelete(item.stock_code)" style="color:var(--red);">删除</button>
                </template>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 分析技能 -->
    <div class="card">
      <h3 style="margin-bottom:16px;font-size:1rem;">🔧 分析技能（6 维度）</h3>
      <p style="color:var(--text-secondary);font-size:0.85rem;margin-bottom:16px;">
        当前所有技能默认启用，后续版本支持自定义开关。
      </p>
      <div style="display:grid;grid-template-columns:repeat(auto-fill, minmax(280px, 1fr));gap:12px;">
        <div
          v-for="skill in skills"
          :key="skill.name"
          style="padding:12px 16px;background:var(--bg-subtle);border-radius:var(--radius-sm);border:1px solid var(--border-light);"
        >
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
            <span style="font-weight:600;">{{ skill.display }}</span>
            <span class="tag active" style="font-size:0.7rem;">已启用</span>
          </div>
          <p style="font-size:0.8rem;color:var(--text-muted);">{{ skill.desc }}</p>
        </div>
      </div>
    </div>
  </div>
</template>
