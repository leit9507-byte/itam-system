import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

export default defineConfig({
  plugins: [
    vue(),
    AutoImport({
      resolvers: [ElementPlusResolver({ importStyle: 'css' })]
    }),
    Components({
      resolvers: [ElementPlusResolver({ importStyle: 'css' })]
    })
  ],
  build: {
    chunkSizeWarningLimit: 800,
    modulePreload: {
      resolveDependencies: () => []
    },
    rollupOptions: {
      output: {
        manualChunks(id) {
          const normalizedId = id.replaceAll('\\', '/')
          const pageChunks = [
            ['src/views/report/', 'page-report'],
            ['src/views/stocktake/', 'page-stocktake'],
            ['src/views/audit/', 'page-audit'],
            ['src/views/repair/', 'page-repair'],
            ['src/views/dashboard/', 'page-dashboard'],
            ['src/views/permission/', 'page-permission'],
            ['src/views/asset/list.vue', 'page-asset-list']
          ]
          const pageChunk = pageChunks.find(([path]) => normalizedId.includes(path))
          if (pageChunk) return pageChunk[1]

          if (!normalizedId.includes('node_modules')) return
          if (normalizedId.includes('/node_modules/vue/') || normalizedId.includes('/node_modules/vue-router/') || normalizedId.includes('/node_modules/pinia/')) {
            return 'vendor-vue'
          }
          if (normalizedId.includes('/node_modules/@element-plus/icons-vue/')) {
            return 'vendor-element-icons'
          }
          if (normalizedId.includes('/node_modules/element-plus/theme-chalk/')) {
            return 'vendor-element-style'
          }
          if (normalizedId.includes('/node_modules/element-plus/')) {
            return 'vendor-element'
          }
          if (normalizedId.includes('/node_modules/zrender/')) {
            return 'vendor-zrender'
          }
          if (normalizedId.includes('/node_modules/echarts/')) {
            return 'vendor-echarts'
          }
          if (normalizedId.includes('/node_modules/axios/')) {
            return 'vendor-http'
          }
          return 'vendor'
        }
      }
    }
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
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
