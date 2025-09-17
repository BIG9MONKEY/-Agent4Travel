<template>
    <div class="sidebar_right light-theme">
      <div class="top-section">
        <div class="header-container">
          <button @click="prevImage">⏪</button>
          <h2 class="center-text">{{ current.name }}</h2>
          <button @click="nextImage">⏩</button>
        </div>
        <div class="image-container">
          <img :src="current.img" alt="景点图片" />
        </div>
      </div>
      <div class="bottom-section">
        <h2>天气预报</h2>
        <ul>
          <li v-for="(w, i) in weather" :key="i">{{ w }}</li>
        </ul>
      </div>
    </div>
  </template>
  
  <script setup>
  import { ref, onMounted } from 'vue'
  
  const weather = ref([])
  const index = ref(0)
  const attractions = ref([
    { name: '北京故宫', img: '/图标.png' },
    { name: '颐和园', img: '/图标.png' },
  ])
  const current = ref(attractions.value[index.value])
  
  function nextImage() {
    index.value = (index.value + 1) % attractions.value.length
    current.value = attractions.value[index.value]
  }
  function prevImage() {
    index.value = (index.value - 1 + attractions.value.length) % attractions.value.length
    current.value = attractions.value[index.value]
  }
  
  onMounted(() => {
    fetch('http://127.0.0.1:3200/weather', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ location: '北京' })
    })
      .then(r => r.json())
      .then(data => weather.value = data.weather || [])
  })
  </script>
  