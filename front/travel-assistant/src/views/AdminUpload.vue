<template>
  <div class="admin-upload">
    <div class="header">
      <h1 style="color: white;">管理员界面</h1>
      <button class="logout-button" @click="handleLogout">退出登录</button>
    </div>
    <div class="upload-container">
      <FileUpload />
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import FileUpload from '../components/FileUpload.vue'

const router = useRouter()
   
   /*
   当用户点击退出登录时：
   1.清除 adminToken
   2.使用 router.push('/') 跳转回首页
   */
const handleLogout = () => {// 退出登录时跳转到首页
  localStorage.removeItem('adminToken')
  router.push('/')// 使用 router.push 进行跳转
}



// 保存原始 body 样式
let originalBodyBackgroundImage = ''
let originalBodyBackgroundSize = ''
let originalBodyBackgroundPosition = ''
let originalBodyBackgroundRepeat = ''
let originalBodyBackgroundAttachment = ''

onMounted(() => {
  // 检查是否已登录
  const token = localStorage.getItem('adminToken')
  if (!token) {
    router.push('/')
  } else {
    // 保存原始 body 样式
    originalBodyBackgroundImage = document.body.style.backgroundImage
    originalBodyBackgroundSize = document.body.style.backgroundSize
    originalBodyBackgroundPosition = document.body.style.backgroundPosition
    originalBodyBackgroundRepeat = document.body.style.backgroundRepeat
    originalBodyBackgroundAttachment = document.body.style.backgroundAttachment

    // 设置新的 body 背景
    document.body.style.backgroundImage = "url('/image/壁纸.png')"
    document.body.style.backgroundSize = "cover"
    document.body.style.backgroundPosition = "center"
    document.body.style.backgroundRepeat = "no-repeat"
    document.body.style.backgroundAttachment = "fixed" // 背景固定，不随滚动条滚动
  }
})

onUnmounted(() => {
  // 恢复原始 body 背景
  document.body.style.backgroundImage = originalBodyBackgroundImage
  document.body.style.backgroundSize = originalBodyBackgroundSize
  document.body.style.backgroundPosition = originalBodyBackgroundPosition
  document.body.style.backgroundRepeat = originalBodyBackgroundRepeat
  document.body.style.backgroundAttachment = originalBodyBackgroundAttachment
})
</script>

<style scoped>
.admin-upload {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-bottom: 30px;
}

.header h1 {
  margin: 0;
  font-size: 24px;
  color: #333;
}

.logout-button {
  position: absolute;
  right: 20px;
  padding: 8px 16px;
  background-color: #dc3545;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.logout-button:hover {
  background-color: #c82333;
}

.upload-container {
  background-color: white;
  margin-top:350px;
  padding: 50px;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}


</style> 