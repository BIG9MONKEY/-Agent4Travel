<template>
  <div class="weather-card">
    <div class="weather-header">
      <h2 class="city-name" v-if="currentCityName" id="location_name">{{ currentCityName }}</h2>
      <h2 class="city-name" v-else>等待检测目的地...</h2>
    </div>

    <div v-if="currentCityName" class="attraction-section">
      <div class="attraction-header">
        <button class="nav-button" @click="prevAttraction">&lt;</button>
        <h3 class="attraction-name">{{ currentAttraction.name || '加载中...' }}</h3>
        <button class="nav-button" @click="nextAttraction">&gt;</button>
      </div>
      <div class="attraction-image-container">
        <img
          :src="currentAttraction.imageUrl || '/default-attraction.jpg'"
          :alt="currentAttraction.name"
          class="attraction-image"
          @error="handleImageError"
        />
      </div>
    </div>

    <div v-else class="no-destination">
      <p>默认显示北京的天气信息。您可以在聊天中提及您想去的目的地，如"我想去上海旅游"</p>
    </div>

    <div v-if="currentCityName" class="weather-section">
      <h3 class="weather-title">天气预报</h3>

      <div class="forecast-container">
        <div
          v-for="(day, index) in weatherData?.forecast || []"
          :key="index"
          class="forecast-day"
          :id="`day-${index + 1}`"
        >
          <div class="forecast-content">
            <span class="day-text">{{ day }}</span>

            <!-- 展示多个天气图标 -->
            <div class="weather-icon-container">
              <div v-for="(weatherType, i) in splitWeatherTypes(getForecastDesc(day))" :key="i">
                <img
                  :src="getWeatherIconPath(weatherType)"
                  :alt="weatherType"
                  class="weather-icon"
                  @error="handleWeatherIconError"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch, inject, onUnmounted } from 'vue';
import { getWeatherByCityName, getCityAttractions } from '../services/api';

export default {
  name: 'WeatherCard',
  props: {
    chatHistory: {
      type: Array,
      default: () => []
    }
  },
  setup(props) {
    const detectedRegion = inject('detectedRegion', ref(null));
    const sessions = inject('sessions', ref([]));
    const currentSessionId = inject('currentSessionId', ref(null));
    
    console.log('WeatherCard初始检测到的区域:', detectedRegion.value);
    
    const currentCity = computed(() => {
      // 直接使用detectedRegion，它由ChatBox组件管理，优先显示会话内容中检测到的地区
      const region = detectedRegion.value;
      console.log('WeatherCard计算当前城市，检测区域为:', region);
      return region || '北京';
    });
    const weatherData = ref(null);
    const attractions = ref([]);
    const currentAttractionIndex = ref(0);
    const defaultImageUrl = '/default-attraction.jpg';

    const currentCityName = computed(() => currentCity.value);
    const currentAttraction = computed(() => {
      if (!attractions.value.length) {
        return { name: '暂无景点信息', imageUrl: defaultImageUrl };
      }
      return attractions.value[currentAttractionIndex.value];
    });

    // 添加测试函数，用于开发调试
    const testUpdateWeather = (cityName) => {
      console.log(`测试函数调用: 更新天气信息为 ${cityName}`);
      if (cityName && typeof cityName === 'string') {
        detectedRegion.value = cityName;
      } else {
        console.error('城市名称无效');
      }
    };

    // 暴露测试函数到全局，方便调试
    if (typeof window !== 'undefined') {
      window.testUpdateWeather = testUpdateWeather;
    }

    const nextAttraction = () => {
      if (attractions.value.length > 0) {
        currentAttractionIndex.value = (currentAttractionIndex.value + 1) % attractions.value.length;
      }
    };

    const prevAttraction = () => {
      if (attractions.value.length > 0) {
        currentAttractionIndex.value = (currentAttractionIndex.value - 1 + attractions.value.length) % attractions.value.length;
      }
    };

    const handleImageError = (event) => {
      if (attractions.value.length > 1) {
        nextAttraction();
      } else {
        event.target.src = defaultImageUrl;
      }
    };

    const handleWeatherIconError = (event) => {
      event.target.src = '/climate/多云.png';
    };

    const getForecastDesc = (forecast) => {
      if (!forecast) return '';
      const parts = forecast.split(/[,，]/);
      if (parts.length >= 3) return parts[2].trim();
      const match = forecast.match(/\d+℃\s*~\s*\d+℃\s*(.+)/);
      if (match) return match[1].trim();
      return ['多云', '晴', '阴', '小雨', '中雨', '大雨', '暴雨', '雷阵雨', '阵雨', '雾']
        .find(w => forecast.includes(w)) || '多云';
    };

    const splitWeatherTypes = (desc) => {
      if (!desc) return ['多云'];
      return desc.split(/[转\/]/).map(t => t.trim()).filter(Boolean);
    };

    const getWeatherIconPath = (weatherType) => {
      const knownTypes = ['多云', '晴', '阴', '小雨', '中雨', '大雨', '暴雨', '雷阵雨', '阵雨', '雾', '大暴雨'];
      if (knownTypes.includes(weatherType)) {
        return `/climate/${weatherType}.png`;
      }
      for (const type of knownTypes) {
        if (weatherType.includes(type)) {
          return `/climate/${type}.png`;
        }
      }
      return '/climate/多云.png';
    };

    const fetchWeatherForCity = async () => {
      try {
        weatherData.value = await getWeatherByCityName(currentCity.value);
      } catch (error) {
        console.error('天气数据获取失败', error);
      }
    };

    const fetchAttractionsForCity = async () => {
      try {
        const result = await getCityAttractions(currentCity.value);
        if (Array.isArray(result)) {
          attractions.value = result.map(attraction => ({
            name: attraction.name || '未知景点',
            imageUrl: attraction.imageUrl || defaultImageUrl
          }));
        }
      } catch (err) {
        console.error('景点数据获取失败', err);
      }
    };

    const updateCurrentDisplay = async () => {
      await fetchWeatherForCity();
      await fetchAttractionsForCity();
    };

    let carouselInterval = null;
    const startCarousel = () => {
      carouselInterval = setInterval(() => {
        if (attractions.value.length > 1) nextAttraction();
      }, 5000);
    };

    // 添加监听sessionStorage变化的函数
    const handleStorageChange = (event) => {
      if (event.key === 'lastDetectedRegion' || event.key === 'regionFromSessionName') {
        // 当相关的存储项变化时，检查会话名称中的地区
        if (typeof window !== 'undefined' && window.sessionStorage) {
          const regionFromSessionNameFlag = window.sessionStorage.getItem('regionFromSessionName')
          if (regionFromSessionNameFlag === 'true') {
            const lastRegion = window.sessionStorage.getItem('lastDetectedRegion')
            if (lastRegion && lastRegion !== detectedRegion.value) {
              console.log(`WeatherCard: 会话名称提取的地区已更新: ${lastRegion}`);
              detectedRegion.value = lastRegion;
              updateCurrentDisplay();
            }
          }
        }
      }
    };

    onMounted(async () => {
      // 首先检查sessionStorage中是否有从会话名称中提取的地区
      if (typeof window !== 'undefined' && window.sessionStorage) {
        const regionFromSessionNameFlag = window.sessionStorage.getItem('regionFromSessionName')
        if (regionFromSessionNameFlag === 'true') {
          const lastRegion = window.sessionStorage.getItem('lastDetectedRegion')
          if (lastRegion) {
            console.log(`WeatherCard: 使用会话名称中提取的地区: ${lastRegion}`);
            detectedRegion.value = lastRegion;
          }
        }
        
        // 添加存储事件监听器
        window.addEventListener('storage', handleStorageChange);
      }
      
      // 如果没有从会话名称中提取到地区，使用默认值
      if (!detectedRegion.value) {
        console.log('WeatherCard: 未检测到区域，默认设置为北京');
        detectedRegion.value = '北京';
      } else {
        console.log('WeatherCard: 已有检测到的区域:', detectedRegion.value);
      }
      await updateCurrentDisplay();
      startCarousel();
    });

    onUnmounted(() => {
      if (carouselInterval) clearInterval(carouselInterval);
      
      // 移除存储事件监听器
      if (typeof window !== 'undefined') {
        window.removeEventListener('storage', handleStorageChange);
      }
    });

    // 监听会话ID变化，刷新天气
    watch(currentSessionId, (newId, oldId) => {
      console.log(`WeatherCard: 会话从 ${oldId} 切换到 ${newId}`);
      if (newId && detectedRegion.value) {
        console.log(`WeatherCard: 会话切换，当前地区为 ${detectedRegion.value}`);
        updateCurrentDisplay();
      }
    });
    
    // 监听检测到的地区变化，立即更新天气
    watch(detectedRegion, (newRegion, oldRegion) => {
      console.log(`WeatherCard: 检测区域从 ${oldRegion || '无'} 变为 ${newRegion || '无'}`);
      if (newRegion) {
        console.log(`WeatherCard: 开始获取 ${newRegion} 的天气数据`);
        updateCurrentDisplay();
      }
    }, { immediate: true });

    watch(() => props.chatHistory, () => {
      updateCurrentDisplay();
    }, { deep: true });

    return {
      currentCityName,
      weatherData,
      attractions,
      currentAttractionIndex,
      currentAttraction,
      nextAttraction,
      prevAttraction,
      handleImageError,
      handleWeatherIconError,
      getForecastDesc,
      splitWeatherTypes,
      getWeatherIconPath
    };
  }
};
</script>

<style scoped>
.weather-card {
  background-color: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 0;
  width: 100%;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  border-left: 1px solid #eee;
}

/* 城市导航区 */
.weather-header {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 15px;
  background-color: #e3f2fd;
  border-bottom: 1px solid #e0e0e0;
  flex-shrink: 0;
}

.city-name {
  font-size: 20px;
  font-weight: bold;
  text-align: center;
  color: #1976d2;
}

/* 景点标题 */
.attraction-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 15px;
  border-bottom: 1px solid #f0f0f0;
}

.attraction-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  margin-bottom: 10px;
}

.nav-button {
  background-color: #f3f3f3;
  border: none;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s;
  font-size: 16px;
  color: #1976d2;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.nav-button:hover {
  background-color: #e3f2fd;
  transform: scale(1.05);
}

.attraction-name {
  font-size: 16px;
  font-weight: 600;
  text-align: center;
  color: #333;
  margin: 0 10px;
  flex: 1;
}

/* 景点图片区域 */
.attraction-image-container {
  position: relative;
  width: 100%;
  height: 220px;
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 3px 6px rgba(0,0,0,0.1);
}

.attraction-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.3s ease;
}

.attraction-image:hover {
  transform: scale(1.05);
}

/* 天气预报区 */
.weather-section {
  display: flex;
  flex-direction: column;
  padding: 15px;
  overflow-y: auto;
}

.weather-title {
  font-size: 18px;
  font-weight: 600;
  text-align: center;
  color: #1976d2;
  margin: 10px 0 15px 0;
  padding: 10px 0;
  border-radius: 0;
  background-color: #f5f5f5;
}

.current-weather {
  display: flex;
  align-items: center;
  margin-bottom: 15px;
  background-color: #f9f9f9;
  padding: 15px;
  border-radius: 10px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.temp-container {
  display: flex;
  align-items: flex-start;
  margin-right: 15px;
}

.temperature {
  font-size: 28px;
  font-weight: bold;
  color: #e67e22;
}

.degree {
  font-size: 16px;
  color: #888;
  margin-top: 2px;
}

.weather-info {
  flex: 1;
}

.weather-desc {
  font-size: 16px;
  color: #333;
  margin-bottom: 5px;
}

.weather-detail {
  font-size: 12px;
  color: #666;
}

.loading-weather {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100px;
  background-color: #f9f9f9;
  padding: 20px;
  border-radius: 10px;
}

.forecast-container {
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  max-height: 300px;
  padding-right: 5px;
}

.forecast-day {
  padding: 12px 15px;
  border-bottom: 1px solid #f0f0f0;
  transition: background-color 0.2s;
  border-radius: 8px;
  margin-bottom: 5px;
}

.forecast-day:hover {
  background-color: #f9f9f9;
}

.forecast-content {
  display: flex;
  align-items: center;
  font-size: 14px;
  color: #333;
  justify-content: space-between;
}

.weather-icon-container {
  display: flex;
  align-items: center;
}

.weather-icon-container > div {
  display: inline-flex;
}

.weather-icon {
  width: 24px;
  height: 24px;
  margin-left: 4px;
  vertical-align: middle;
}

.no-destination {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 200px;
  padding: 20px;
  background-color: #f9f9f9;
  text-align: center;
  color: #666;
  font-size: 14px;
  border-radius: 10px;
  margin: 15px;
}

/* 滚动条样式 */
.forecast-container::-webkit-scrollbar {
  width: 5px;
}

.forecast-container::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 5px;
}

.forecast-container::-webkit-scrollbar-thumb {
  background: #ccc;
  border-radius: 5px;
}

.forecast-container::-webkit-scrollbar-thumb:hover {
  background: #999;
}

@media (max-width: 768px) {
  .attraction-image-container {
    height: 180px;
  }
  
  .forecast-container {
    max-height: 250px;
  }
}
</style>
