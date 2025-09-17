<template>
  <main class="main-layout">
    <div class="sidebar-container" id="sidebar-container">
      <Sidebar @toggle-sidebar="toggleSidebar" />
    </div>
    <button id="toggle-sidebar-collapsed" class="toggle-sidebar-collapsed" @click="toggleSidebar" title="展开会话记录">
      <span class="arrow-icon">&#9654;</span>
    </button>
    <div class="chat-container-wrapper" id="chat-container-wrapper">
      <ChatBox />
    </div>
    <div class="weather-container">
      <WeatherCard :chat-history="getChatHistoryArray()" />
    </div>
  </main>
</template>

<script setup>
import { provide, ref, computed, watch, onMounted } from 'vue'
import Sidebar from '../components/Sidebar.vue'
import ChatBox from '../components/ChatBox.vue'
import WeatherCard from '../components/WeatherCard.vue'

// 全局状态
const currentSessionId = ref(null)
const chatHistory = ref({})
const activeStreams = ref({})
const sessions = ref([])
const detectedRegion = ref(null)

// 从localStorage加载会话列表
function loadSessions() {
  const savedSessions = localStorage.getItem('sessions')
  if (savedSessions) {
    sessions.value = JSON.parse(savedSessions)
  }
}

// 保存会话列表到localStorage
function saveSessions() {
  localStorage.setItem('sessions', JSON.stringify(sessions.value))
}

// 从localStorage加载当前会话ID
function loadCurrentSessionId() {
  const savedId = localStorage.getItem('currentSessionId')
  if (savedId) {
    currentSessionId.value = savedId
  }
}

// 保存当前会话ID到localStorage
function saveCurrentSessionId() {
  localStorage.setItem('currentSessionId', currentSessionId.value)
}

// 监听currentSessionId的变化
watch(currentSessionId, (newId) => {
  saveCurrentSessionId()
})

// 计算属性，获取当前会话的消息数组
const getChatHistoryArray = () => {
  if (!currentSessionId.value || !chatHistory.value[currentSessionId.value]) {
    return [];
  }
  
  return chatHistory.value[currentSessionId.value].messages.map(msg => ({
    role: msg.sender === 'user' ? 'user' : 'assistant',
    content: msg.content,
    time: msg.timestamp
  }));
};

// 监听聊天历史变化
watch(chatHistory, () => {
  console.log('聊天历史更新，可能包含新的目的地信息');
}, { deep: true });

// 提供全局状态给子组件
provide('currentSessionId', currentSessionId)
provide('chatHistory', chatHistory)
provide('activeStreams', activeStreams)
provide('detectedRegion', detectedRegion)
provide('sessions', sessions)

// 切换侧边栏
function toggleSidebar() {
  const sidebarContainer = document.getElementById('sidebar-container');
  const chatContainer = document.getElementById('chat-container-wrapper');
  const toggleButton = document.getElementById('toggle-sidebar-collapsed');
  
  if (sidebarContainer && chatContainer && toggleButton) {
    const isCollapsed = sidebarContainer.classList.toggle('collapsed');
    chatContainer.classList.toggle('expanded');
    toggleButton.classList.toggle('show');
    
    if (isCollapsed) {
      const arrowIcon = toggleButton.querySelector('.arrow-icon');
      if (arrowIcon) {
        arrowIcon.innerHTML = '&#9654;';
      }
      toggleButton.title = '展开会话记录';
    } else {
      toggleButton.title = '展开会话记录';
    }
  }
}

// 初始化
onMounted(() => {
  loadSessions()
  loadCurrentSessionId()
  
  if (sessions.value.length === 0) {
    const defaultId = Date.now().toString()
    sessions.value.push({
      id: defaultId,
      name: '新会话',
      timestamp: new Date().toISOString()
    })
    currentSessionId.value = defaultId
    saveSessions()
  }
  
  const toggleButton = document.getElementById('toggle-sidebar-collapsed');
  if (toggleButton) {
    toggleButton.classList.remove('show');
  }
})
</script>

<style scoped>
.main-layout {
  display: flex;
  flex: 1;
  overflow: hidden;
  position: relative;
  width: 100%;
  max-width: 100%;
  padding: 0;
  gap: 0;
  margin-top: 49px;
}

.sidebar-container {
  width: 250px;
  background-color: #fff;
  flex-shrink: 0;
  overflow: hidden;
  box-shadow: none;
  border-right: 1px solid #eee;
  border-radius: 0;
  transition: width 0.3s ease;
  position: fixed;
  left: 0;
  top: 49px;
  bottom: 0;
  z-index: 10;
}

.sidebar-container.collapsed {
  width: 0;
  overflow: hidden;
}

.chat-container-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: #fff;
  overflow: hidden;
  border-radius: 0;
  box-shadow: none;
  min-width: 0;
  transition: all 0.3s ease;
  margin-left: 20px;
  margin-right: 20px;
  width: calc(100% - 100px);
  max-width: 2500px;
  padding: 0 0px;
}

.chat-container-wrapper.expanded {
  margin-left: 100px;
  width: calc(100% - 430px);
}

.toggle-sidebar-collapsed {
  position: fixed;
  top: 60px;
  left: 0;
  width: 24px;
  height: 50px;
  background-color: #e9f0f7;
  border: 1px solid #c8d8e8;
  border-radius: 0 6px 6px 0;
  display: none;
  align-items: center;
  justify-content: center;
  z-index: 11;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.3s ease, background-color 0.2s ease, border-color 0.2s ease;
}

.toggle-sidebar-collapsed.show {
  opacity: 1;
  display: flex;
}

.toggle-sidebar-collapsed:hover {
  background-color: #d3e4f5;
  border-color: #a9c5e0;
}

.toggle-sidebar-collapsed .arrow-icon {
  font-size: 16px;
  font-weight: bold;
  color: #1976d2;
  text-shadow: 0 1px 1px rgba(0,0,0,0.1);
  transition: all 0.3s ease;
}

.toggle-sidebar-collapsed:hover .arrow-icon {
  color: #0d5aa7;
  transform: translateX(2px);
}

.weather-container {
  width: 330px;
  display: flex;
  flex-direction: column;
  background-color: #fff;
  flex-shrink: 0;
  overflow-y: auto;
  box-shadow: none;
  border-left: 1px solid #eee;
  border-radius: 0;
  transition: width 0.3s ease;
  position: fixed;
  right: 0;
  top: 49px;
  bottom: 0;
  z-index: 10;
}

@media (max-width: 1200px) {
  .main-layout {
    flex-direction: column;
    overflow-y: auto;
    height: auto;
    max-height: none;
    margin-top: 49px;
    padding: 0;
    gap: 0;
  }
  
  .sidebar-container {
    width: 100%;
    height: auto;
    position: relative;
    top: auto;
    left: auto;
    bottom: auto;
    flex-shrink: 0;
    max-height: 200px;
    margin-right: 0;
    border-radius: 0;
    border-bottom: 1px solid #eee;
    border-right: none;
    box-shadow: none;
    overflow: hidden;
  }
  
  .chat-container-wrapper {
    flex: 1;
    min-height: 400px;
    max-height: 60vh;
    margin: 0;
    width: 100%;
    margin-left: 0;
    margin-right: 0;
    border-radius: 0;
    box-shadow: none;
    border-bottom: 1px solid #eee;
  }
  
  .weather-container {
    width: 100%;
    position: relative;
    top: auto;
    right: auto;
    bottom: auto;
    flex-shrink: 0;
    max-height: 500px;
    margin-left: 0;
    border-radius: 0;
    border-left: none;
    box-shadow: none;
  }
}

@media (max-width: 768px) {
  .main-layout {
    flex-direction: column;
    padding: 5px;
    gap: 5px;
  }
  
  .chat-container-wrapper {
    max-height: 50vh;
  }
  
  .weather-container {
    max-height: 450px;
  }
}
</style> 