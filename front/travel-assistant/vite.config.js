import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    proxy: {
      // 将 /api/chat 转发到 /chain/pdf_retrieval
      '/api/chat': {
        target: 'http://localhost:3200',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/chat/, '/chain/pdf_retrieval')
      },
      // 将其他 /api 开头的请求转发到后端服务器
      '/api': {
        target: 'http://localhost:3200',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
})
