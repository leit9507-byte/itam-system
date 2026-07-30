import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

export default defineConfig({
  plugins: [
    vue(),
    AutoImport({
      resolvers: [ElementPlusResolver({ importStyle: false })]
    }),
    Components({
      resolvers: [ElementPlusResolver({ importStyle: false })]
    })
  ],
  optimizeDeps: {
    include: [
      'vue',
      'vue-router',
      'pinia',
      'axios',
      'echarts',
      'element-plus',
      'element-plus/es',
      '@element-plus/icons-vue'
    ]
  },
  build: {
    target: 'es2018',
    cssTarget: 'chrome61',
    chunkSizeWarningLimit: 800,
    modulePreload: {
      resolveDependencies: () => []
    }
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    allowedHosts: ['it.forevernine.net'],
    watch: {
      // Windows/macOS 的 Docker 挂载不传递文件变更事件，容器内需轮询才能热更新
      usePolling: process.env.CHOKIDAR_USEPOLLING === 'true',
      interval: 300
    },
    proxy: {
      '/backend': {
        target: process.env.VITE_BACKEND_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
        rewrite: path => path.replace(/^\/backend/, '')
      }
    }
  }
})
