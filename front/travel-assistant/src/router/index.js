import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import AdminUpload from '../views/AdminUpload.vue'

const routes = [
  {
    path: '/',// 首页路由
    name: 'home',
    component: Home
  },
  {
    path: '/admin/upload', // 管理员上传页面路由
    name: 'admin-upload',
    component: AdminUpload,
    meta: { requiresAuth: true }// 需要认证
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
/**当用户访问 /admin/upload 时：
路由守卫会检查是否有 adminToken
如果没有 token，自动跳转到首页
如果有 token，允许访问上传页面 **/
router.beforeEach((to, from, next) => {
  if (to.matched.some(record => record.meta.requiresAuth)) {
    const token = localStorage.getItem('adminToken')
    if (!token) {
      next('/')
    } else {
      next()
    }
  } else {
    next()
  }
})

export default router 