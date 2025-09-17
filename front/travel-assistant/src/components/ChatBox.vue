<template>
    <div class="chat-container" id="chat-container">
      <div class="scroll-container">
        <div class="chat-box" id="chat-box">
          <div
            v-for="(msg, idx) in displayMessages"
            :key="idx"
            :class="['chat-message', msg.sender]"
            :data-session-id="currentSessionId">
            <img class="avatar" :src="msg.sender === 'user' ? '/image/users.png' : '/image/ai2.png'" alt="头像" />
            <div class="message" v-html="msg.displayContent"></div>
          </div>
        </div>
      </div>
      <InputBox @send="handleSend" />
    </div>
  </template>
  
  <script setup>
  import { ref, watch, computed, inject, onMounted, nextTick, provide } from 'vue'
  import InputBox from './InputBox.vue'
  import showdown from 'showdown'
  import { sendChatMessage, detectDestination } from '../services/api'
  
  const currentSessionId = inject('currentSessionId')
  const chatHistory = inject('chatHistory')
  const activeStreams = inject('activeStreams')
  
  // 注入由App.vue提供的detectedRegion变量，而不是创建新的
  const detectedRegion = inject('detectedRegion')
  const sessions = inject('sessions', ref([]))
  
  // 标记是否从会话名称中提取了地区
  const regionFromSessionName = ref(false)
  
  // 创建一个 showdown 转换器并配置
  const converter = new showdown.Converter({
    simpleLineBreaks: true,    // 使用简单的换行处理
    strikethrough: true,       // 支持删除线
    tables: true,              // 支持表格
    tasklists: true,           // 支持任务列表
    smartIndentationFix: true, // 智能缩进修复
    disableForced4SpacesIndentedSublists: true, // 禁用强制4空格缩进子列表
    emoji: true,               // 支持emoji
    openLinksInNewWindow: true, // 链接在新窗口打开
    parseImgDimensions: true,  // 解析图片尺寸
    literalMidWordUnderscores: true, // 允许词中下划线
    customizedHeaderId: true,  // 自定义标题ID
    ghCodeBlocks: true,        // 支持GitHub风格代码块
    ghCompatibleHeaderId: true, // GitHub兼容的标题ID
    splitAdjacentBlockquotes: true, // 分割相邻的引用块
    underline: true,           // 支持下划线
    noHeaderId: false          // 产生标题ID
  })
  
  // 计算当前会话的消息
  const displayMessages = computed(() => {
    if (!currentSessionId.value || !chatHistory.value[currentSessionId.value]) {
      return []
    }
    
    return chatHistory.value[currentSessionId.value].messages.map(msg => {
      // 转换markdown为HTML
      let displayContent = msg.content
      if (msg.sender === 'bot') {
        displayContent = converter.makeHtml(msg.content)
        // 不再添加光标
      }
      
      return {
        ...msg,
        displayContent
      }
    })
  })
  
  // 检查是否有从会话名称中提取的地区标记
  onMounted(() => {
    if (typeof window !== 'undefined' && window.sessionStorage) {
      const regionFromSessionNameFlag = window.sessionStorage.getItem('regionFromSessionName')
      if (regionFromSessionNameFlag === 'true') {
        regionFromSessionName.value = true
        
        // 如果有存储的地区信息，直接使用
        const lastRegion = window.sessionStorage.getItem('lastDetectedRegion')
        if (lastRegion && !detectedRegion.value) {
          console.log(`聊天框: 从会话存储中恢复地区信息: ${lastRegion}`)
          detectedRegion.value = lastRegion
        }
      }
    }
  })
  
  // 监听currentSessionId的变化，切换会话时重新检测目的地
  watch(currentSessionId, (newSessionId, oldSessionId) => {
    if (newSessionId !== oldSessionId) {
      console.log(`聊天框: 会话从 ${oldSessionId} 切换到 ${newSessionId}`)
      
      // 检查sessionStorage中是否有标记
      if (typeof window !== 'undefined' && window.sessionStorage) {
        const regionFromSessionNameFlag = window.sessionStorage.getItem('regionFromSessionName')
        if (regionFromSessionNameFlag === 'true') {
          regionFromSessionName.value = true
          
          // 如果有存储的地区信息，直接使用
          const lastRegion = window.sessionStorage.getItem('lastDetectedRegion')
          if (lastRegion) {
            console.log(`聊天框: 使用会话存储中的地区信息: ${lastRegion}`)
            detectedRegion.value = lastRegion
            return // 如果已经从会话名称中提取到地区，不再进行其他检测
          }
        } else {
          regionFromSessionName.value = false
        }
      }
      
      // 优先从会话名称中提取地区（改变优先级）
      const nameCheckResult = checkSessionNameForRegion(newSessionId)
      
      // 如果从会话名称中没有检测到地区，才尝试从聊天内容中检测
      if (!nameCheckResult && chatHistory.value[newSessionId] && chatHistory.value[newSessionId].messages) {
        const messages = chatHistory.value[newSessionId].messages
        
        // 找出最近的用户消息
        const userMessages = messages
          .filter(msg => msg.sender === 'user')
          .map(msg => msg.content)
          .slice(-3)
        
        // 从聊天内容中检测目的地
        if (userMessages.length > 0) {
          console.log('聊天框: 从会话名称未检测到地区，尝试从会话内容中检测目的地...')
          // 使用最新的一条消息来检测
          detectDestination(userMessages[userMessages.length - 1])
            .then(region => {
              if (region) {
                console.log(`聊天框: 从会话历史中检测到目的地: ${region}`)
                detectedRegion.value = region
              }
            })
            .catch(err => {
              console.error('检测目的地出错:', err)
            })
        }
      }
      
      // 刷新聊天窗口
      nextTick(() => {
        scrollToBottom()
      })
    }
  }, { immediate: true })
  
  // 从会话名称中检测地区的辅助函数
  function checkSessionNameForRegion(sessionId) {
    const session = sessions.value.find(s => s.id === sessionId)
    if (!session) return false
    
    const sessionName = session.name
    if (!sessionName || sessionName === '新会话') return false
    
    console.log(`聊天框: 尝试从会话名称 "${sessionName}" 中提取地区`);
    
    // 检查名称中是否包含地区信息
    const nameMatch = sessionName.match(/(.+)(旅游|之行|游记|旅行|一日游|旅程|游玩|观光|游览)/)
    
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
      if (sessionName.includes(location)) {
        regionFromSessionName.value = true
        console.log(`聊天框: 从会话名称 "${sessionName}" 中精确匹配到地区: ${location}`)
        detectedRegion.value = location
        return true
      }
    }
    
    // 如果精确匹配失败，尝试解析格式化的名称
    if (nameMatch && nameMatch[1]) {
      const extractedRegion = nameMatch[1].trim()
      
      // 不完全匹配时，排除过于简短的地名以避免误判
      if (extractedRegion.length >= 2) {
        regionFromSessionName.value = true
        console.log(`聊天框: 从会话名称 "${sessionName}" 中提取到可能的地区: ${extractedRegion}`)
        detectedRegion.value = extractedRegion
        return true
      }
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
      const match = sessionName.match(pattern)
      if (match && match[1] && match[1].length >= 2) {
        regionFromSessionName.value = true
        console.log(`聊天框: 从会话名称 "${sessionName}" 中提取到可能的地区: ${match[1]}`)
        detectedRegion.value = match[1]
        return true
      }
    }
    
    console.log(`聊天框: 无法从会话名称 "${sessionName}" 中提取到地区信息`);
    return false
  }
  
  // 当会话ID变化时，滚动到底部
  watch(currentSessionId, async () => {
    await nextTick()
    scrollToBottom()
  })
  
  // 当消息变化时，滚动到底部
  watch(displayMessages, async () => {
    await nextTick()
    scrollToBottom()
  }, { deep: true })
  
  // 添加一个响应式变量来控制光标显示
  const isTyping = ref(false)
  
  // 处理发送消息
  async function handleSend({ text, language }) {
    if (!text.trim()) return
    
    const sessionId = currentSessionId.value
    
    // 如果当前有正在进行的流处理，取消它
    if (activeStreams.value[sessionId]) {
      // TODO: 实现取消流
      activeStreams.value[sessionId] = false
      console.log("已停止之前的回复")
      
      // 确保任何进行中的消息都设置为非流式
      if (chatHistory.value[sessionId]) {
        const messages = chatHistory.value[sessionId].messages
        for (let i = messages.length - 1; i >= 0; i--) {
          if (messages[i].sender === 'bot' && messages[i].isStreaming) {
            messages[i].isStreaming = false
            break
          }
        }
      }
    }
    
    // 保存用户消息到历史记录
    saveMessageToHistory(sessionId, text, 'user')
    
    // 立即添加一个空的机器人消息到历史记录，并显示闪烁光标
    saveMessageToHistory(sessionId, '', 'bot', true)
    isTyping.value = true
    
    // 滚动到最新消息
    await nextTick()
    scrollToBottom()
    
    // 检查是否已经从会话名称中提取了地区（regionFromSessionName为true表示已提取）
    // 如果会话名称已提取地区，则保留当前地区信息，不再从消息中检测
    if (!regionFromSessionName.value) {
      try {
        console.log('聊天框: 从会话名称未提取地区，尝试从用户消息中检测目的地:', text);
        const destinationResult = await detectDestination(text);
        if (destinationResult) {
          console.log(`聊天框: 从用户消息中检测到目的地: ${destinationResult}`);
          detectedRegion.value = destinationResult;
        }
      } catch (error) {
        console.error('检测目的地失败:', error);
      }
    } else {
      console.log('聊天框: 已从会话名称中提取地区，保留当前地区信息:', detectedRegion.value);
    }
    
    try {
      // 使用API服务发送请求
      const response = await sendChatMessage(text, sessionId, language)
      
      // 获取响应流
      const reader = response.body.getReader()
      await processStream(reader, sessionId)
      
      // 如果之前未检测到目的地且会话名称未提取地区，尝试从回复中检测
      if (!detectedRegion.value && !regionFromSessionName.value) {
        try {
          console.log('聊天框: 从回复中检测目的地...');
          const region = await detectDestination(response.reply);
          if (region) {
            console.log('聊天框: 从回复中检测到目的地:', region);
            detectedRegion.value = region;
          } 
        } catch (error) {
          console.error('从回复中检测目的地时出错:', error);
        }
      }
      
    } catch (error) {
      console.error('发送消息时出错:', error)
      
      // 关闭光标并显示错误消息
      isTyping.value = false
      
      // 添加错误消息到历史记录
      saveMessageToHistory(sessionId, '抱歉，发生了错误，请稍后再试。', 'bot')
    }
  }
  
  // 处理流式响应
  async function processStream(reader, sessionId) {
    // 标记当前会话流处理开始
    activeStreams.value[sessionId] = true
    isTyping.value = true // 确保整个流程中isTyping保持为true
    
    let botMessageContent = ''
    const chatBox = document.getElementById('chat-box')
    
    // 记录创建时的会话ID
    const originalSessionId = currentSessionId.value
    
    // 不再创建新消息，而是使用handleSend中已创建的空消息
    await nextTick()
    
    // 只有当前显示的是这个会话时，才创建DOM消息容器
    let containerInDOM = null
    if (currentSessionId.value === sessionId) {
      containerInDOM = document.querySelector(`.chat-message.bot[data-session-id="${sessionId}"]:last-child`)
    }
    
    // 定义一个显示内容的函数
    const updateContent = (content) => {
      if (!containerInDOM) {
        // 如果DOM元素不存在，可能是切换了会话，只更新历史记录
        updateLastBotMessage(sessionId, content, true)
        return
      }
      
      const messageDiv = containerInDOM.querySelector('.message')
      if (!messageDiv) return
      
      // 检查是否是第一次更新内容（从加载状态变为实际内容）
      const isFirstContent = messageDiv.querySelector('.loading-message')
      
      if (isFirstContent) {
        // 如果是第一次有实际内容，使用淡入效果替换加载状态
        messageDiv.classList.add('transitioning')
      }
      
      // 渲染内容
      messageDiv.innerHTML = converter.makeHtml(content)
      
      // 移除过渡类和done类，允许动画效果
      messageDiv.classList.remove('transitioning')
      messageDiv.classList.remove('done')
      
      // 滚动到底部
      chatBox.scrollTop = chatBox.scrollHeight
    }
    
    try {
      while (true) {
        const { done, value } = await reader.read()
        
        if (done) {
          console.log(`流式响应结束，会话 ${sessionId}`)
          console.log("最终内容:", botMessageContent)
          
          // 清除最后一条机器人的 isStreaming 状态
          if (chatHistory.value[sessionId]) {
            const messages = chatHistory.value[sessionId].messages
            for (let i = messages.length - 1; i >= 0; i--) {
              if (messages[i].sender === 'bot') {
                messages[i].isStreaming = false
                break
              }
            }
          }
          
          // 更新为最终版本
          updateLastBotMessage(sessionId, botMessageContent, false)
          
          activeStreams.value[sessionId] = false
          isTyping.value = false
          return
        }
        
        // 将流式数据解码为字符串
        const text = new TextDecoder().decode(value)
        console.log(`接收到数据块，会话 ${sessionId}:`, text)
        
        try {
          // 解析 JSON 数据
          const data = JSON.parse(text)
          if (data.answer) {
            // 直接添加新的内容块
            botMessageContent += data.answer
            
            // 确保持续设置isStreaming状态
            if (chatHistory.value[sessionId]) {
              const messages = chatHistory.value[sessionId].messages
              for (let j = messages.length - 1; j >= 0; j--) {
                if (messages[j].sender === 'bot') {
                  messages[j].isStreaming = true
                  break
                }
              }
            }
            
            // 更新isTyping确保显示光标
            isTyping.value = true
            
            // 只有当前显示的是这个会话，且仍是创建时的会话时，才更新DOM
            if (currentSessionId.value === sessionId && originalSessionId === currentSessionId.value) {
              updateContent(botMessageContent)
            } else {
              // 否则只更新历史记录，不更新DOM
              updateLastBotMessage(sessionId, botMessageContent, true)
            }
          }
        } catch (e) {
          console.error(`解析JSON数据出错 (session ${sessionId}):`, e)
          continue
        }
      }
    } catch (error) {
      console.error('处理流式响应出错:', error)
      activeStreams.value[sessionId] = false
      isTyping.value = false
      
      // 确保在出错时也设置isStreaming为false
      if (chatHistory.value[sessionId]) {
        const messages = chatHistory.value[sessionId].messages
        for (let i = messages.length - 1; i >= 0; i--) {
          if (messages[i].sender === 'bot' && messages[i].isStreaming) {
            messages[i].isStreaming = false
            break
          }
        }
      }
      
      updateLastBotMessage(sessionId, '抱歉，处理响应时发生了错误。', false)
    }
  }
  
  // 保存消息到历史记录
  function saveMessageToHistory(sessionId, content, sender, isTyping = false) {
    if (!chatHistory.value[sessionId]) {
      chatHistory.value[sessionId] = {
        messages: [],
        needsRebuild: false
      }
    }
    
    const message = {
      id: Date.now().toString(),
      content: content,
      sender: sender,
      timestamp: new Date().toISOString(),
      isStreaming: sender === 'bot' && isTyping // 明确设置isStreaming属性
    }
    
    if (sender === 'bot' && isTyping) {
      // 使用一个简单的加载占位内容，不使用光标
      message.displayContent = '<div class="loading-message">机器人正在思考中...</div>'
    }
    
    chatHistory.value[sessionId].messages.push(message)

    // 如果是添加空的机器人消息，立即滚动到底部
    if (sender === 'bot' && isTyping) {
      nextTick(() => {
        scrollToBottom()
      })
    }
  }
  
  // 更新最后一条机器人消息
  function updateLastBotMessage(sessionId, content, isStreaming = false) {
    if (!chatHistory.value[sessionId]) return;

    const messages = chatHistory.value[sessionId].messages;

    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].sender === 'bot') {
        messages[i].content = content;
        messages[i].isStreaming = isStreaming;

        // Markdown 转 HTML
        let html = converter.makeHtml(content);
        
        // 不添加光标
        messages[i].displayContent = html;
        break;
      }
    }

    nextTick(() => {
      scrollToBottom();
    });
  }
  
  // 滚动到底部
  function scrollToBottom() {
    const chatBox = document.getElementById('chat-box')
    if (chatBox) {
      chatBox.scrollTop = chatBox.scrollHeight
    }
  }
  
  // 初始化
  onMounted(() => {
    // 如果没有当前会话ID，说明是新用户，创建一个默认会话
    if (!currentSessionId.value) {
      currentSessionId.value = Date.now().toString()
      chatHistory.value[currentSessionId.value] = {
        messages: [],
        needsRebuild: false,
      }
    }
  })
  </script>
  
  <style>
  /* 全局样式，已禁用光标 */
  .cursor {
    display: none;
  }
  
  /* 活跃状态的光标 - 已禁用 */
  .active-cursor {
    display: none;
  }
  
  .message.done .cursor {
    display: none !important;
  }
  
  /* 已禁用光标动画 */
  @keyframes blink-animation {
    0%, 100% { opacity: 0; }
  }
  
  /* 已禁用激活光标动画 */
  @keyframes active-blink-animation {
    0%, 100% { opacity: 0; }
  }
  </style>
  
  <style scoped>
  .chat-container {
    display: flex;
    flex-direction: column;
    height: calc(100vh - 49px);
    background-color: #fff;
    position: relative;
    overflow: hidden;
    border-left: none;
    border-right: none;
    margin: 0 auto;
    width: 100%;
  }
  
  .scroll-container {
    flex: 1;
    overflow-y: auto;
    padding: 0px 0px;
    scroll-behavior: smooth;
  }
  
  .chat-box {
    display: flex;
    flex-direction: column;
    gap: 0px;
    padding-bottom: 0px;
    max-width: 90%; /* 增加对话内容最大宽度 */
    margin: 0 auto;
    width: 100%;
    padding: 0 10px; /* 添加左右内边距 */
  }
  
  .chat-message {
    display: flex;
    max-width: 90%; /* 增加最大宽度 */
    margin-bottom: 15px;
    animation: fadeIn 0.3s ease;
  }
  
  @keyframes fadeIn {
    from { opacity: 0.7; }
    to { opacity: 1; }
  }
  
  .chat-message.user {
    align-self: flex-end;
    flex-direction: row-reverse;
    margin-right: 0; /* 贴近右侧 */
  }
  
  .chat-message.user .message {
    background-color: #e1f5fe; /* 用户消息使用蓝色背景 */
    padding: 15px 20px;
    border-radius: 10px 2px 10px 10px; /* 右上角更尖锐 */
    margin: 20px 15px 15px 0;
    box-shadow: 0 1px 2px rgba(0,0,0,0.1);
  }
  
  .chat-message.bot {
    align-self: flex-start;
    margin-left: 0; /* 贴近左侧 */
  }
  
  .chat-message.bot .message {
    background-color: #f5f5f5;
    padding: 10px 15px;
    border-radius: 2px 10px 10px 10px;
    margin: 0 0 0 8px;
    color: #333;
    max-width: 100%; /* 允许占用全部空间 */
    line-height: 1.6;
    font-size: 1em;
    letter-spacing: 0.2px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.1);
  }
  
  .avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    object-fit: cover;
    flex-shrink: 0;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
  }
  
  .message {
    text-align: left;
    animation: fadeIn 0.3s ease;
    margin-bottom: 8px;
  }
  
  .message p {
    margin: 0 0 4px 0;
    line-height: 1.4;
    text-align: left;
  }
  
  .message p:last-child {
    margin-bottom: 0;
  }
  
  .message h2,
  .message h3 {
    margin: 1px 0 1px 0;
    padding: 0;
    text-align: left;
    color: #2196f3;
    font-weight: bold;
  }
  
  .message ul,
  .message ol {
    margin: 0;
    padding-left: 20px;
  }
  
  .message li {
    margin: 2px 0;
    line-height: 1.4;
    text-align: left;
  }
  
  .message strong {
    color: #2196f3;
    font-weight: bold;
  }
  
  .message code {
    background: #f5f5f5;
    padding: 2px 4px;
    border-radius: 4px;
    font-family: monospace;
  }
  
  .message pre {
    background: #f5f5f5;
    padding: 8px;
    border-radius: 4px;
    overflow-x: auto;
    margin: 4px 0;
  }
  
  .message pre code {
    background: none;
    padding: 0;
  }
  
  .message.done {
    animation: fadeIn 0.3s ease;
  }
  
  .message.done .cursor, 
  .message.done .blinking {
    display: none;
  }
  
  /* 优化加载消息样式 */
  .loading-message {
    color: #666;
    font-style: italic;
    padding: 5px 0;
    display: flex;
    align-items: center;
    gap: 5px;
  }
  
  /* 移除光标样式 */
  
  /* 针对时间标题的特殊样式 */
  .message h3 {
    position: relative;
    padding-left: 24px;
    margin: 8px 0 4px 0;
    font-size: 1.15em;
    color: #333;
    font-weight: 600;
    text-align: left;
  }
  
  .message h3::before {
    content: '🕒';
    position: absolute;
    left: 0;
    top: 50%;
    transform: translateY(-50%);
    font-size: 1em;
  }
  
  .message p {
    margin: 0 0 4px 0;
    line-height: 1.5;
    text-align: left;
  }
  
  .message p:last-child {
    margin-bottom: 0;
  }
  
  .message ul, .message ol {
    margin: 2px 0 4px 0;
    padding-left: 24px;
    text-align: left;
  }
  
  .message li {
    margin-bottom: 2px;
    line-height: 1.4;
    text-align: left;
  }
  
  .message em {
    font-style: normal;
    color: #555;
  }
  
  /* 针对特殊标题的样式 */
  .message h2 {
    font-size: 1.2em;
    margin: 16px 0 10px 0;
    padding-bottom: 6px;
    border-bottom: 1px solid #eee;
    color: #333;
    text-align: left;
  }
  
  @media (max-width: 1200px) {
    .chat-container {
      height: 100%;
    }
  }
  
  .message pre {
    background-color: #f0f0f0;
    padding: 10px;
    border-radius: 5px;
    overflow-x: auto;
    margin: 10px 0;
  }
  
  .message code {
    font-family: 'Courier New', Courier, monospace;
    background-color: #f0f0f0;
    padding: 2px 4px;
    border-radius: 3px;
  }
  
  /* 添加初始加载状态的样式 */
  .chat-message.bot .message:empty::after {
    content: "机器人正在思考中...";
    color: #888;
    font-style: italic;
    display: inline-block;
    margin-left: 5px;
  }
  
  /* 添加打字机效果的样式 */
  .typing-effect {
    overflow: hidden;
    border-right: 2px solid #333;
    white-space: nowrap;
    margin: 0 auto;
    letter-spacing: 0.1em;
    animation: typing 3.5s steps(40, end), blink-caret 0.75s step-end infinite;
  }
  
  @keyframes typing {
    from { width: 0 }
    to { width: 100% }
  }
  
  @keyframes blink-caret {
    from, to { border-color: transparent }
    50% { border-color: #333 }
  }
  
  /* 添加内容过渡效果 */
  .message.transitioning {
    opacity: 0.7;
    transition: opacity 0.3s ease;
  }
  
  .message.transitioning:not(.transitioning) {
    opacity: 1;
  }
  </style>