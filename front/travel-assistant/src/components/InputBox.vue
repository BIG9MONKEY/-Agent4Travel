<template>
    <div id="input-box" class="input-box">
      <div class="language-dropdown">
        <input type="text" id="language-input" class="language-input" placeholder="输入语言" v-model="language">
        <div class="language-dropdown-content">
          <button @click="setLanguage('中文')">中文</button>
          <button @click="setLanguage('英文')">英文</button>
          <button @click="setLanguage('西班牙语')">西班牙语</button>
          <button @click="setLanguage('法语')">法语</button>
          <button @click="setLanguage('德语')">德语</button>
        </div>
      </div>
      <input 
        type="text" 
        class="user-input" 
        v-model="message" 
        placeholder="你想去哪里？" 
        @keypress.enter="send">
      <button class="send-button" @click="send">
        <img src="/image/上传.png" alt="发送" class="send-icon">
      </button>

      <!-- 推荐问题区域 -->
      <div class="suggestions-container" v-if="showSuggestions">
        <button
          class="suggestion-button"
          v-for="question in suggestedQuestions"
          :key="question"
          @click="useSuggestion(question)"
        >
          {{ question }}
        </button>
      </div>
    </div>
  </template>
  
  <script setup>
  import { ref, inject } from 'vue'
  
  const emit = defineEmits(['send'])
  const currentSessionId = inject('currentSessionId')
  const chatHistory = inject('chatHistory')
  
  const message = ref('')
  const language = ref('')
  const showSuggestions = ref(true)
  
  // 从这些问题中随机选择三个作为推荐问题
  const allSuggestedQuestions = [
    "详细介绍该地区的旅游景点。",
    "规划一下旅游路线！",
    "介绍一下该地区的文化特色。",
    "推荐几个适合旅游的城市。",
    "给出去这里旅游的注意事项。",
    "推荐一些特产和美食。",
    "推荐一些纪念品。"
  ]
  
  // 随机选择3个问题
  const suggestedQuestions = ref(getRandomQuestions())
  
  function setLanguage(lang) {
    language.value = lang
  }
  
  function send() {
    if (!message.value.trim()) return
    
    emit('send', { 
      text: message.value, 
      language: language.value 
    })
    
    // 清空输入框
    message.value = ''
    
    // 更新推荐问题
    suggestedQuestions.value = getRandomQuestions()
  }
  
  function useSuggestion(question) {
    message.value = question
    send()
  }
  
  // 随机获取推荐问题
  function getRandomQuestions(count = 3) {
    return [...allSuggestedQuestions]
      .sort(() => 0.5 - Math.random())
      .slice(0, count)
  }
  </script>
  
  <style scoped>
  .input-box {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    align-items: center;
    padding: 1em;
    background-color: #f4f4f9;
    border-top: 1px solid #ddd;
    border-radius: 50px;
    margin: 10px 40px 20px 40px;
  }
  
  .language-dropdown {
    position: relative;
    display: inline-block;
    margin-right: 10px;
  }
  
  .language-input {
    width: 80px;
    padding: 8px 10px;
    border: 1px solid #ddd;
    border-radius: 15px;
    font-size: 14px;
  }
  
  .language-dropdown-content {
    display: none;
    position: absolute;
    bottom: 100%;
    left: 0;
    background-color: #f9f9f9;
    min-width: 120px;
    box-shadow: 0px 8px 16px 0px rgba(0,0,0,0.2);
    z-index: 1;
    border-radius: 5px;
  }
  
  .language-dropdown-content button {
    color: black;
    padding: 10px 15px;
    text-decoration: none;
    display: block;
    border: none;
    width: 100%;
    text-align: left;
    background-color: transparent;
    cursor: pointer;
    font-size: 14px;
  }
  
  .language-dropdown-content button:hover {
    background-color: #f1f1f1;
  }
  
  .language-dropdown:hover .language-dropdown-content {
    display: block;
  }
  
  .user-input {
    flex: 1;
    padding: 10px 15px;
    border: 1px solid #ddd;
    border-radius: 20px;
    font-size: 15px;
  }
  
  .send-button {
    background-color: #4caf50;
    border: none;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    justify-content: center;
    align-items: center;
    color: white;
    cursor: pointer;
    margin-left: 10px;
    transition: background-color 0.3s;
  }
  
  .send-button:hover {
    background-color: #3d9140;
  }
  
  .send-icon {
    width: 18px;
    height: 18px;
    object-fit: contain;
  }
  
  .suggestions-container {
    width: 100%;
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    margin-top: 10px;
  }
  
  .suggestion-button {
    background-color: #f0f0f0;
    border: 1px solid #ddd;
    border-radius: 15px;
    padding: 8px 15px;
    margin: 5px;
    cursor: pointer;
    font-size: 14px;
    transition: background-color 0.3s;
  }
  
  .suggestion-button:hover {
    background-color: #e0e0e0;
  }

  .input-area {
    display: flex;
    align-items: center;
    padding: 10px;
    border-top: 1px solid #e0e0e0;
    background-color: #fff;
    position: relative;
    flex-shrink: 0;
  }
  </style>
  