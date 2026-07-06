import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  build: {
    chunkSizeWarningLimit: 800,
    rollupOptions: {
      output: {
        manualChunks(id) {
          const normalizedId = id.replaceAll('\\', '/')
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
    proxy: {
      '/backend': {
        target: process.env.VITE_BACKEND_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
        rewrite: path => path.replace(/^\/backend/, '')
      }
    }
  }
})
