<template>
  <div class="sidebar" id="sidebar">
    <div class="scroll-container">
      <ul id="conversation-list">
        <li
          v-for="session in sessions"
          :key="session.id"
          :class="['conversation-item', { active: currentSessionId === session.id }]"
          @click="selectConversation(session)"
          ref="conversationItems"
        >
          <div class="item-content">
            <span class="conversation-title">{{ session.name }}</span>
          </div>
          <div class="item-actions">
            <button class="menu-button" @click.stop="showMenu(session, $event)">⋮</button>
          </div>
        </li>
      </ul>

      <!-- 独立渲染 menu-content -->
      <div
        v-if="activeMenuSession"
        class="menu-content"
        :style="{ top: `${menuPosition.top}px`, left: `${menuPosition.left}px` }"
      >
        <button @click.stop="renameConversation(activeMenuSession.id)">重命名</button>
        <button @click.stop="deleteConversation(activeMenuSession)">删除</button>
      </div>
    </div>

    <button class="new-conversation" @click="newConversation" title="添加会话">&#x271A;</button>
    <button id="toggle-sidebar" class="toggle-sidebar" @click="toggleSidebar" title="收起会话记录">
      <span class="arrow-icon">&#9664;</span>
    </button>
  </div>
</template>

<script setup>
import { ref, inject, onMounted, watch, nextTick, defineEmits } from 'vue'

const emits = defineEmits(['toggle-sidebar'])

const currentSessionId = inject('currentSessionId')
const chatHistory = inject('chatHistory')
const detectedRegion = inject('detectedRegion')

const sessions = ref([])
const dialogVisible = ref(false)
const currentSession = ref(null)
const newTitle = ref('')
const activeMenuSession = ref(null)
const menuPosition = ref({ top: 0, left: 0 })

// 从localStorage加载会话列表
const loadSessionsFromStorage = () => {
  const savedSessions = localStorage.getItem('travelAssistantSessions')
  if (savedSessions) {
    try {
      const loadedSessions = JSON.parse(savedSessions)
      // 确保每个会话都有showMenu属性
      sessions.value = loadedSessions.map(session => ({
        ...session,
        showMenu: false
      }))
      console.log('从本地存储加载会话列表:', sessions.value)
    } catch (e) {
      console.error('加载会话列表出错:', e)
      sessions.value = []
    }
  }
}

// 保存会话列表到localStorage
const saveSessionsToStorage = () => {
  localStorage.setItem('travelAssistantSessions', JSON.stringify(sessions.value))
  console.log('保存会话列表到本地存储')
}

// 初始化：加载会话列表
onMounted(() => {
  // 加载会话列表
  loadSessionsFromStorage()
  
  // 如果会话列表为空，创建默认会话
  if (sessions.value.length === 0) {
    newConversation()
  } else {
    // 如果有会话，选择第一个
    selectConversation(sessions.value[0])
  }
  
  // 从localStorage加载聊天历史
  const savedChatHistory = localStorage.getItem('travelAssistantChatHistory')
  if (savedChatHistory) {
    try {
      const parsedHistory = JSON.parse(savedChatHistory)
      // 合并历史记录，不覆盖当前内存中的历史
      Object.keys(parsedHistory).forEach(sessionId => {
        if (!chatHistory.value[sessionId]) {
          chatHistory.value[sessionId] = parsedHistory[sessionId]
        }
      })
      console.log('从本地存储加载聊天历史')
    } catch (e) {
      console.error('加载聊天历史出错:', e)
    }
  }

  // 添加点击外部关闭菜单的事件监听
  document.addEventListener('click', (event) => {
    // 如果点击的不是菜单按钮或菜单内容，则关闭菜单
    const menuButton = event.target.closest('.menu-button')
    const menuContent = event.target.closest('.menu-content')
    if (!menuButton && !menuContent) {
      activeMenuSession.value = null
    }
  })
})

// 监听会话列表变化，保存到localStorage
watch(sessions, () => {
  saveSessionsToStorage()
}, { deep: true })

// 监听聊天历史变化，保存到localStorage
watch(chatHistory, () => {
  localStorage.setItem('travelAssistantChatHistory', JSON.stringify(chatHistory.value))
  console.log('保存聊天历史到本地存储')
}, { deep: true })

// 创建新会话
function newConversation() {
  const newId = Date.now().toString()
  const newName = `新会话 ${sessions.value.length + 1}`
  sessions.value.push({
    id: newId,
    name: newName,
    timestamp: new Date().toISOString(),
    showMenu: false
  })
  
  // 记录当前检测到的地区，以便稍后恢复
  const previousRegion = detectedRegion.value;
  
  // 切换到新会话
  currentSessionId.value = newId;
  
  // 如果之前有检测到的地区，保持不变
  if (previousRegion) {
    console.log(`保持之前检测到的地区: ${previousRegion}`);
    detectedRegion.value = previousRegion;
  }
  
  saveSessionsToStorage();
}

// 选择会话
function selectConversation(session) {
  // 关闭所有菜单
  sessions.value.forEach(s => s.showMenu = false)
  
  // 设置当前会话
  currentSessionId.value = session.id
  console.log('切换到会话:', session.name, '(ID:', session.id, ')')
  
  // 从会话名称中提取地区并更新天气信息
  const region = extractRegionFromName(session.name)
  if (region) {
    console.log(`Sidebar: 从会话名称 "${session.name}" 中提取到地区: ${region}，优先使用此地区信息`)
    
    // 定义一个事件对象，传递给ChatBox和WeatherCard组件
    const eventData = {
      source: 'sessionName',
      sessionId: session.id,
      region: region,
      timestamp: Date.now()
    }
    
    // 更新检测到的地区
    detectedRegion.value = region
    
    // 设置sessionStorage标记，表示这个地区是从会话名称中提取的，应该优先使用
    if (typeof window !== 'undefined' && window.sessionStorage) {
      window.sessionStorage.setItem('regionFromSessionName', 'true')
      window.sessionStorage.setItem('lastDetectedRegion', region)
    }
  } else {
    console.log('未从会话名称中提取到地区，从聊天内容检测地区将由ChatBox组件完成')
    // 清除sessionStorage中的标记
    if (typeof window !== 'undefined' && window.sessionStorage) {
      window.sessionStorage.removeItem('regionFromSessionName')
    }
  }
}

// 显示菜单
function showMenu(session, event) {
  // 如果点击的是当前打开菜单的会话，则关闭菜单
  if (activeMenuSession.value === session) {
    activeMenuSession.value = null
    return
  }

  // 设置新的活动菜单会话
  activeMenuSession.value = session

  nextTick(() => {
    const buttonRect = event.target.getBoundingClientRect()
    const containerRect = document.querySelector('.scroll-container').getBoundingClientRect()

    menuPosition.value = {
      top: buttonRect.bottom - containerRect.top + 4,
      left: buttonRect.right - containerRect.left - 120,
    }
  })
}

// 重命名会话
function renameConversation(id) {
  const session = sessions.value.find(s => s.id === id)
  if (session) {
    const newName = prompt('请输入新的会话名称：', session.name)
    if (newName && newName.trim()) {
      session.name = newName.trim()
      saveSessionsToStorage()
      
      // 从新的会话名称中提取地区并更新天气信息
      const region = extractRegionFromName(newName.trim())
      if (region) {
        console.log(`从重命名的会话名称 "${newName.trim()}" 中提取到地区: ${region}`)
        detectedRegion.value = region
      }
    }
  }
  // 关闭菜单
  activeMenuSession.value = null
}

// 从会话名称中提取目的地
function extractRegionFromName(name) {
  if (!name || name === '新会话') return null;
  
  console.log(`Sidebar: 尝试从会话名称 "${name}" 中提取地区`);
  
  // 常见的城市名称后缀
  const suffixes = ['市', '区', '县', '省', '自治区']
  // 移除后缀
  let region = name
  for (const suffix of suffixes) {
    if (region.endsWith(suffix)) {
      region = region.slice(0, -suffix.length)
      break;
    }
  }
  
  // 检查一些特殊情况，如"xx旅游"，"xx之行"
  const patterns = [/(.+)(旅游|之行|游记|旅行|一日游|旅程|游玩|观光|游览)/]
  for (const pattern of patterns) {
    const match = region.match(pattern)
    if (match && match[1]) {
      region = match[1]
      break;
    }
  }
  
  // 扩展常见的旅游地点列表，提高匹配率
  const commonLocations = [
    '香港', '澳门', '台湾', '北京', '上海', '广州', '深圳', '杭州', 
    '成都', '重庆', '西安', '南京', '厦门', '三亚', '丽江', '大理',
    '苏州', '青岛', '哈尔滨', '大连', '拉萨', '日照', '桂林', '昆明',
    '武汉', '长沙', '郑州', '天津', '济南', '宁波', '无锡', '南宁',
    '长春', '沈阳', '乌鲁木齐', '西宁', '海口', '贵阳', '福州', '九寨沟',
    '张家界', '敦煌', '兰州', '银川', '呼和浩特', '太原', '合肥', '南昌'
  ]
  
  // 优先精确匹配常见地点
  for (const location of commonLocations) {
    if (name.includes(location)) {
      console.log(`Sidebar: 从会话名称 "${name}" 中精确匹配到地区: ${location}`);
      return location;
    }
  }
  
  // 再次检查移除后缀、模式匹配后的地区名
  if (region && region.length >= 2 && region !== name) {
    console.log(`Sidebar: 从会话名称 "${name}" 中提取到可能的地区: ${region}`);
    return region;
  }
  
  // 尝试提取任何可能包含的地名
  const locationPatterns = [
    /去([^去]+)/, 
    /在([^在]+)/, 
    /到([^到]+)/, 
    /游([^游]+)/, 
    /玩([^玩]+)/, 
    /游览([^游览]+)/, 
    /观光([^观光]+)/
  ]
  
  for (const pattern of locationPatterns) {
    const match = name.match(pattern)
    if (match && match[1] && match[1].length >= 2) {
      const extractedRegion = match[1].trim();
      console.log(`Sidebar: 从会话名称 "${name}" 中提取到可能的地区: ${extractedRegion}`);
      return extractedRegion;
    }
  }
  
  console.log(`Sidebar: 无法从会话名称 "${name}" 中提取到地区信息`);
  return null;
}

// 删除监听currentSessionId的watch处理，ChatBox组件已经处理了会话切换时的地区检测
// watch(currentSessionId, (newId) => {
//   if (newId) {
//     const session = sessions.value.find(s => s.id === newId)
//     if (session) {
//       const region = extractRegionFromName(session.name)
//       if (region) {
//         detectedRegion.value = region
//       }
//     }
//   }
// }, { immediate: true })

// 删除会话
function deleteConversation(session) {
  if (confirm(`确定要删除会话 "${session.name}" 吗？`)) {
    const index = sessions.value.findIndex(s => s.id === session.id)
    if (index !== -1) {
      // 获取当前会话的地区信息
      const currentSessionRegion = detectedRegion.value;
      
      // 是否删除的是当前会话
      const isDeletingCurrentSession = currentSessionId.value === session.id;
      
      // 删除会话
      sessions.value.splice(index, 1)
      
      // 删除聊天历史
      delete chatHistory.value[session.id]
      
      // 如果删除的是当前会话，选择另一个会话
      if (isDeletingCurrentSession) {
        if (sessions.value.length > 0) {
          // 选择另一个会话，但暂时不更新地区信息
          const nextSession = sessions.value[0];
          currentSessionId.value = nextSession.id;
          
          // 尝试从新选择的会话名称中提取地区
          const regionFromName = extractRegionFromName(nextSession.name);
          if (regionFromName) {
            console.log(`从新选择的会话 "${nextSession.name}" 中提取到地区: ${regionFromName}`);
            detectedRegion.value = regionFromName;
          } else {
            console.log('没有从新会话名称提取到地区');
          }
        } else {
          // 如果没有会话了，创建一个新的，保留原有地区信息
          const preservedRegion = currentSessionRegion;
          newConversation();
          if (preservedRegion) {
            console.log(`保留之前的地区信息: ${preservedRegion}`);
            detectedRegion.value = preservedRegion;
          }
        }
      }
    }
  }
  // 关闭菜单
  activeMenuSession.value = null;
}

// 切换侧边栏显示
function toggleSidebar() {
  // 触发父组件的事件处理函数
  emits('toggle-sidebar')
}
</script>

<style scoped>
.sidebar {
  width: 100%;
  height: 100%;
  background-color: #f5f5f5;
  padding: 10px;
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  position: relative;
  overflow: hidden; /* 防止内部内容溢出 */
  border-right: 1px solid #ddd;
}

/* 增加折叠侧边栏样式 */
.sidebar.collapsed {
  width: 0;
  padding: 0;
  opacity: 0;
}

.scroll-container {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 5px;
  width: 100%;
  position: relative; /* 关键：让菜单定位基于这个容器 */
}

#conversation-list {
  list-style: none;
  padding: 0;
  margin: 0;
  width: 100%; /* 确保列表宽度为100% */
}

.conversation-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 27px 15px;
  border-radius: 8px;
  margin-bottom: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  background-color: #fff;
  border-left: 3px solid transparent;
  width: 90%;
  box-sizing: border-box;
  position: relative;
  z-index: 1;
}

.conversation-item:hover {
  background-color: #f0f0f0;
  transform: translateX(2px);
}

.conversation-item.active {
  background-color: #e3f2fd;
  border-left: 3px solid #1976d2;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  z-index: 1;
}

.item-content {
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  min-width: 0;
}

.conversation-title {
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  color: #333;
}

.item-actions {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 2;
}

.menu-button {
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 20px;
  padding: 0 5px;
  color: #666;
  transition: color 0.2s;
}

.menu-button:hover {
  color: #1976d2;
}

.menu-content {
  position: absolute;
  background-color: #fff;
  border: 1px solid #ddd;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  z-index: 999;
  min-width: 120px;
  overflow: hidden;
}

.menu-content button {
  display: block;
  width: 100%;
  padding: 10px 16px;
  text-align: left;
  background: none;
  border: none;
  cursor: pointer;
  transition: background-color 0.2s;
  font-size: 13px;
  color: #333;
}

.menu-content button:hover {
  background-color: #f0f0f0;
}

.new-conversation {
  margin-top: 10px;
  padding: 12px;
  background-color: #1976d2;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 16px;
  transition: background-color 0.2s;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.new-conversation:hover {
  background-color: #1565c0;
}

.toggle-sidebar {
  position: absolute;
  top: 50%;
  right: 0px; /* 调整位置，使按钮靠近边缘 */
  transform: translateY(-50%);
  width: 24px; /* 增加宽度 */
  height: 50px; /* 增加高度，使按钮更易点击 */
  background-color: #e9f0f7; /* 更改背景色 */
  border: 1px solid #c8d8e8;
  border-radius: 0 6px 6px 0; /* 增加圆角 */
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  box-shadow: 2px 0 5px rgba(0,0,0,0.1);
  transition: all 0.2s ease;
}

.toggle-sidebar:hover {
  background-color: #d3e4f5;
  border-color: #a9c5e0;
}

.arrow-icon {
  font-size: 16px; /* 增加字体大小 */
  font-weight: bold; /* 加粗 */
  color: #1976d2; /* 使用主题色 */
  text-shadow: 0 1px 1px rgba(0,0,0,0.1); /* 添加文本阴影 */
  transition: all 0.3s ease;
}

.toggle-sidebar:hover .arrow-icon {
  color: #0d5aa7; /* 鼠标悬停时颜色变深 */
  transform: translateX(-2px); /* 添加轻微移动效果 */
}
</style>
  