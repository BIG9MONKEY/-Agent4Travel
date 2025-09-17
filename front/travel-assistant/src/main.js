import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './style.css'

// 创建Vue应用实例
const app = createApp(App)

// 使用路由
app.use(router)

// 全局错误处理
app.config.errorHandler = (err, vm, info) => {
  console.error('Vue应用错误:', err)
  console.error('错误组件:', vm)
  console.error('错误信息:', info)
}

// 挂载应用
app.mount('#app')
