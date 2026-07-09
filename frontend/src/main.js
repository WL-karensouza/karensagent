import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router/index.js'
import App from './App.vue'
import './style.css'

const pinia = createPinia()

/* 插件：自动持久化股票分析结果到 localStorage */
pinia.use(({ store }) => {
  /* 只对 stock store 生效 */
  if (store.$id !== 'stock') return

  const KEY = 'stock_last_result'

  /* 从 localStorage 恢复上次结果 */
  try {
    const raw = localStorage.getItem(KEY)
    if (raw) store.analyzeResult = JSON.parse(raw)
  } catch { /* ignore */ }

  /* 监听 analyzeResult 变化，自动持久化 */
  store.$subscribe((mutation, state) => {
    if (state.analyzeResult) {
      localStorage.setItem(KEY, JSON.stringify(state.analyzeResult))
    } else {
      localStorage.removeItem(KEY)
    }
  })
})

const app = createApp(App)
app.use(pinia)
app.use(router)
app.mount('#app')
