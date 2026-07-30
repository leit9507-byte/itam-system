import { createApp } from 'vue'
import { ElLoading } from 'element-plus/es/components/loading/index'
import 'element-plus/dist/index.css'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './styles.css'

const root = document.getElementById('app')

function renderStartupError(error) {
  if (!root) return
  const detail = error instanceof Error ? error.message : String(error || '页面资源加载失败')
  root.innerHTML = `
    <main style="min-height:100vh;display:grid;place-items:center;padding:24px;background:#f4f7fb;font-family:Arial,sans-serif;color:#172033">
      <section style="width:min(100%,420px);padding:24px;background:#fff;border:1px solid #dbe4f0;border-radius:8px">
        <h1 style="margin:0 0 12px;font-size:20px">页面加载失败</h1>
        <p style="margin:0 0 18px;line-height:1.6;color:#64748b;overflow-wrap:anywhere">${escapeHtml(detail)}</p>
        <button type="button" onclick="window.location.reload()" style="width:100%;height:44px;border:0;border-radius:6px;background:#1677ff;color:#fff;font-size:16px">重新加载</button>
      </section>
    </main>
  `
}

function escapeHtml(value) {
  const element = document.createElement('span')
  element.textContent = value
  return element.innerHTML
}

router.onError(renderStartupError)

try {
  const app = createApp(App)
  app.use(createPinia())
  app.use(router)
  app.use(ElLoading)
  app.mount('#app')
} catch (error) {
  renderStartupError(error)
}
