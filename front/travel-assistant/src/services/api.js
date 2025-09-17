// API服务，处理与后端的通信

// 发送聊天消息到服务器
export async function sendChatMessage(message, sessionId, language = null) {
  // 构建请求URL
  let url = `/api/chat?session_id=${sessionId}`
  if (language) {
    url += `&language=${encodeURIComponent(language)}`
  }
  
  // 发送请求
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ 
      input: { input: message },
      config: { configurable: { session_id: sessionId } }
    }),
  })
  
  if (!response.ok) {
    throw new Error(`API请求失败: ${response.status} ${response.statusText}`)
  }
  
  return response
}

// 获取城市景点信息
export async function getHotSpot(location) {
  try {
    const response = await fetch('/api/hotspot', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ location }),
    })
    
    if (!response.ok) {
      throw new Error(`获取景点信息失败: ${response.status}`)
    }
    
    const data = await response.json()
    // 处理后端返回的hotspot字段数据，将景点名称和图片链接格式化为我们需要的格式
    const hotspots = data.hotspot || [];
    
    return hotspots.map(item => ({
      name: item['景点名称'] || item.name || '未知景点', 
      image: item['图片链接'] || item.image || '/image/default.jpg'
    }));
  } catch (error) {
    console.error('获取景点信息时出错:', error)
    return []
  }
}

// 获取天气信息
export async function getWeatherForecast(location) {
  try {
    const response = await fetch('/api/weather', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ location }),
    })
    
    if (!response.ok) {
      throw new Error(`获取天气信息失败: ${response.status}`)
    }
    
    const data = await response.json()
    return data.weather || []
  } catch (error) {
    console.error('获取天气信息时出错:', error)
    return []
  }
}

/**
 * 获取城市的天气数据
 * @param {string} city - 城市名称
 * @returns {Promise<Object>} 天气数据
 */
export async function getWeatherByCityName(city) {
  console.log(`获取城市天气: ${city}`);
  try {
    const response = await fetch('/api/weather', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ location: city })
    });

    if (!response.ok) {
      throw new Error(`获取天气数据失败: ${response.statusText}`);
    }

    const text = await response.text();
    console.log('天气API返回数据:', text);
    
    let data;
    try {
      data = JSON.parse(text);
    } catch (e) {
      console.error('天气数据解析失败:', text);
      throw new Error('无效的天气数据格式: ' + text);
    }
    
    if (!data.weather || !Array.isArray(data.weather)) {
      console.error('无效的天气数据结构:', data);
      throw new Error('无效的天气数据结构');
    }
    
    const weatherItems = data.weather;
    if (weatherItems.length === 0) {
      console.log('天气数据为空');
      return {
        temperature: '--',
        weather: '对不起！无此地区天气信息。',
        humidity: '--',
        wind: '--',
        forecast: []
      };
    } else {
      console.log(`收到 ${weatherItems.length} 天的天气数据`);
      
      // 处理每一天的数据，确保格式一致
      const processedForecasts = weatherItems.map(day => {
        // 如果天气数据不包含逗号或顿号，尝试进行格式化 
        if (!day.includes(',') && !day.includes('，')) {
          // 尝试匹配日期和温度
          const dateMatch = day.match(/(\d{2}\/\d{2}[周星期][一二三四五六日天])/);
          const tempMatch = day.match(/(\d+℃\s*~\s*\d+℃)/);
          
          if (dateMatch && tempMatch) {
            const date = dateMatch[1];
            const temp = tempMatch[1];
            // 查找温度之后的文本作为天气描述
            const afterTemp = day.substring(day.indexOf(temp) + temp.length).trim();
            const weatherDesc = afterTemp || '多云'; // 如果没有描述，默认为多云
            
            // 格式化为 "日期, 温度, 天气描述" 格式
            return `${date}, ${temp}, ${weatherDesc}`;
          }
        }
        
        // 如果没有成功格式化，直接返回原始数据
        return day;
      });
      
      // 处理第一天数据作为当前天气
      const todayWeather = processedForecasts[0];
      const weatherParts = todayWeather.split(/[,，]/);
      
      let temperature = '--';
      let weather = '未知';
      let humidity = '--';
      let wind = '--';
      
      // 解析天气数据
      if (weatherParts.length >= 2) {
        // 提取温度信息，例如 "17℃~10℃"
        const tempPart = weatherParts[1].trim();
        if (tempPart.includes('℃')) {
          temperature = tempPart;
        }
        
        // 提取天气描述，例如 "晴 ☀️"
        if (weatherParts.length >= 3) {
          weather = weatherParts[2].trim();
        } else {
          // 如果没有第三部分，尝试从整个字符串中提取天气关键词
          const weatherKeywords = ['多云', '晴', '阴', '小雨', '中雨', '大雨', '暴雨', '雷阵雨', '阵雨', '雾'];
          for (const keyword of weatherKeywords) {
            if (todayWeather.includes(keyword)) {
              weather = keyword;
              break;
            }
          }
        }
        
        // 设置默认湿度和风力
        humidity = '50';
        wind = '微风';
      }
      
      return {
        temperature,
        weather,
        humidity,
        wind,
        forecast: processedForecasts
      };
    }
  } catch (error) {
    console.error('获取天气数据出错:', error);
    throw error;
  }
}

/**
 * 获取城市的景点数据
 * @param {string} city - 城市名称
 * @returns {Promise<Array>} 景点数据数组
 */
export async function getCityAttractions(city) {
  try {
    console.log(`正在获取${city}的景点数据...`);
    const response = await fetch('/api/hotspot', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ location: city })
    });

    if (!response.ok) {
      throw new Error(`获取景点数据失败: ${response.status}`);
    }

    const data = await response.json();
    console.log('获取到的原始景点数据:', data);

    if (!data || !data.hotspot || !Array.isArray(data.hotspot)) {
      console.warn('获取到的景点数据格式不正确');
      return [];
    }

    // 处理景点数据为更易用的格式
    return data.hotspot.map(attraction => {
      // 根据all.json中的数据结构调整字段名
      return {
        name: attraction['景点名称'] || '未知景点',
        imageUrl: attraction['图片链接'] || '/default-attraction.jpg'
      };
    });
  } catch (error) {
    console.error('获取景点数据出错:', error);
    throw error;
  }
}

/**
 * 检测用户消息中提到的目的地
 * @param {string} message - 用户消息
 * @returns {Promise<string|null>} 检测到的目的地，如果没有检测到则返回null
 */
export async function detectDestination(message) {
  try {
    console.log(`正在分析用户消息: ${message}`);
    const response = await fetch('/api/process_message', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ message })
    });

    if (!response.ok) {
      throw new Error(`检测目的地失败: ${response.status}`);
    }

    const data = await response.json();
    console.log('检测目的地结果:', data);
    
    // 如果返回结果包含region字段，则返回该值
    if (data && data.region) {
      console.log(`成功检测到目的地: ${data.region}`);
      return data.region;
    } else {
      console.log('未检测到目的地');
      return null;
    }
  } catch (error) {
    console.error('检测目的地出错:', error);
    return null;
  }
} 