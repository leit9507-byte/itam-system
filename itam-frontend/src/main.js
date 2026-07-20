import { createApp } from 'vue'
import { ElLoading } from 'element-plus/es/components/loading/index'
import 'element-plus/dist/index.css'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './styles.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElLoading)
app.mount('#app')
