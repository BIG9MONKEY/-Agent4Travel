<template>
  <div class="app">
    <header class="header">
      <h1 class="title">智能旅游助手</h1>
      <button class="admin-login-button" @click="showLoginModal = true">管理员登录</button>
    </header>
    <router-view></router-view>
    <LoginModal :show="showLoginModal" @close="showLoginModal = false" @login-success="handleLoginSuccess" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import LoginModal from './components/LoginModal.vue'

const showLoginModal = ref(false)

const handleLoginSuccess = () => {
  showLoginModal.value = false
}
</script>

<style>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 49px;
  background-color: #1976d2;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 20px;
  z-index: 1000;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.title {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 500;
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
}

.admin-login-button {
  position: absolute;
  right: 20px;
  background-color: transparent;
  border: 1px solid white;
  color: white;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s ease;
}

.admin-login-button:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
  line-height: 1.6;
  color: #333;
  background-color: #f5f5f5;
}
</style>