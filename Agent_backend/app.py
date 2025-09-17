import json
from typing import List
from fastapi import FastAPI, Request, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from langserve import add_routes
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import create_retrieval_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_chroma import Chroma
from langchain.chains import create_history_aware_retriever
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
import pinyin
from langchain_community.embeddings import DashScopeEmbeddings
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import asyncio
from app.rag.rag import RagManager
from app.models.model import get_qwen_models
from datetime import datetime, timedelta
from langchain_core.tools import tool
from duckduckgo_search import DDGS
import requests
import pandas as pd
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import MessagesPlaceholder
import mysql.connector
import bcrypt
import jwt
import os
import subprocess
import sys
from functools import wraps
from mysql.connector import Error

#######################获取模型##########################
llm, chat, embed = get_qwen_models()
######################加载城市ID数据#####################
import pandas as pd
import chardet

# 读取文件的二进制内容
city_df = pd.read_csv('China-City-List-latest.csv', encoding='gbk')
print(city_df.head())

#####################导入需要的数据######################
from data import locations, province_dict
store = {}  # 存储聊天消息历史记录的对象，key为session_id，value为消息历史记录的对象
####################导入自定义函数#######################
from function import fetch_weather_data, load_and_split
# 管理会话历史记录，获取会话ID（session_id）所对应的 ChatMessageHistory对象，不存在就创建一个，并将其存储在一个全局字典 store 中，以便后续检索和使用。
def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        # ChatMessageHistory(): 一个用于存储聊天消息历史记录的对象，通常包含用户和 AI 的交互记录。
        store[session_id] = ChatMessageHistory()
    return store[session_id]


# 创建向量存储数据库管理对象
rag = RagManager(host="localhost", port=8000, llm=llm, embed=embed)
retriever = rag.retriever


######################创建Agent####################
# 定义工具函数
@tool
def get_time() -> str:
    """获取当前时间，包括年月日和时间，可用于判断当前月份和季节"""
    now = datetime.now()
    formatted_time = now.strftime("当前时间是：%Y年%m月%d日 %H:%M")
    return formatted_time

# 定义时效性检测工具
@tool
def is_time_sensitive_query(query: str) -> str:
    """
    智能检测用户提问是否属于时效性问题，返回 '是' 或 '否'。
    :param query: 用户输入的查询文本
    :return: 字符串 '是' 表示需要实时搜索，'否' 表示优先知识库检索
    """
    import re
    # 定义时效性关键词列表
    time_keywords = ["最近", "最新", "近期", "近来", "刚刚", "刚", "即将", "现在",
                     "本月", "本周", "今年", "明年", "明天", "当前", "正在进行", "刚结束"]
    # 定义事件相关词
    event_keywords = ["活动", "展览", "演出", "赛事", "比赛", "促销", "优惠", "打折", "节日",
                      "庆典", "开幕", "开业", "上新", "首发"]
    q = query.lower()
    # 匹配时间关键词
    for kw in time_keywords:
        if kw in q:
            return "是"
    # 匹配事件关键词
    for kw in event_keywords:
        if kw in q:
            return "是"
    # 匹配日期或年份模式，如 '2025年6月15日'
    if re.search(r"\d{4}年|\d{1,2}月\d{1,2}日", q):
        return "是"
    return "否"

# 高德地图API Key
AMAP_KEY = "你的高德地图API Key"
# 高德地图附近POI查询工具
@tool
def search_nearby_pois(location: str, keyword: str, radius: int = 1000, city: str = None) -> str:
    """
    使用高德地图API查询附近的兴趣点（POIs）
    :param location: 经纬度，格式为"经度,纬度"（如"116.481028,39.989643"）
    :param keyword: 查询关键词，如"咖啡店"、"景点"、"美食"等
    :param radius: 查询半径，单位米，默认1000米
    :param city: 城市名称，可选
    :return: 附近POI信息的文本描述
    """
    try:
        url = f"https://restapi.amap.com/v5/place/around?key={AMAP_KEY}&keywords={keyword}&location={location}&radius={radius}"
        if city:
            url += f"&city={city}"
        
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == '1' and data['count'] != '0':
                pois = data['pois']
                result = []
                for i, poi in enumerate(pois[:10], 1):  # 限制返回10个POI
                    name = poi.get('name', '未知')
                    address = poi.get('address', '未知地址')
                    distance = poi.get('distance', '未知')
                    type_code = poi.get('type', '未知类型')
                    result.append(f"{i}. {name}\n   地址: {address}\n   距离: {distance}米\n   类型: {type_code}")
                
                return f"在指定位置附近找到{len(pois)}个\"{keyword}\":\n\n" + "\n\n".join(result)
            else:
                return f"未找到附近的\"{keyword}\"，状态码: {data['status']}, 错误信息: {data.get('info', '未知错误')}"
        else:
            return f"API请求失败: {response.status_code}, 响应内容: {response.text}"
    except Exception as e:
        return f"查询附近兴趣点时发生错误: {str(e)}"

# 高德地图路径规划工具
@tool
def plan_travel_route(origin: str, destination: str, waypoints: str = None) -> str:
    """
    使用高德地图API规划旅游路线
    :param origin: 起点经纬度，格式为"经度,纬度"（如"116.481028,39.989643"）
    :param destination: 终点经纬度，格式为"经度,纬度"（如"116.434446,39.90816"）
    :param waypoints: 途经点列表，多个坐标用"|"分隔（如"116.4976,39.9993|116.4928,39.9915"）
    :return: 路径规划结果的文本描述
    """
    try:
        # 为驾车路线规划添加 strategy=10 参数，以获取更稳定和接近App推荐的路线
        url = f"https://restapi.amap.com/v3/direction/driving?key={AMAP_KEY}&origin={origin}&destination={destination}&strategy=10"
        if waypoints:
            url += f"&waypoints={waypoints}"
        
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == '1' and data.get('route', {}).get('paths'):
                paths = data['route']['paths'][0]  # 获取第一条推荐路径
                distance = paths.get('distance', '0')  # 路径距离，单位：米
                duration = paths.get('duration', '0')  # 预计耗时，单位：秒
                tolls = paths.get('tolls', '0')  # 道路收费，单位：元
                toll_distance = paths.get('toll_distance', '0')  # 收费路段长度，单位：米
                
                # 计算小时和分钟
                duration_hours = int(duration) // 3600
                duration_minutes = (int(duration) % 3600) // 60
                time_str = ""
                if duration_hours > 0:
                    time_str += f"{duration_hours}小时"
                if duration_minutes > 0:
                    time_str += f"{duration_minutes}分钟"
                
                # 获取路径详情
                steps = []
                for i, step in enumerate(paths.get('steps', []), 1):
                    instruction = step.get('instruction', '').replace('<[^>]+>', '')  # 去除HTML标签
                    road_name = step.get('road_name', '未知道路')
                    step_distance = step.get('distance', '0')
                    steps.append(f"{i}. {instruction} - {road_name} ({step_distance}米)")
                
                result = f"路线规划结果:\n"
                result += f"总距离: {float(distance)/1000:.1f}公里\n"
                result += f"预计耗时: {time_str}\n"
                if int(tolls) > 0:
                    result += f"道路收费: {tolls}元 (收费路段: {float(toll_distance)/1000:.1f}公里)\n"
                result += "\n详细路线:\n"
                result += "\n".join(steps)  
                
                return result
            else:
                return f"路径规划失败: 状态码: {data['status']}, 错误信息: {data.get('info', '未知错误')}"
        else:
            return f"API请求失败: {response.status_code}, 响应内容: {response.text}"
    except Exception as e:
        return f"规划旅游路线时发生错误: {str(e)}"

# 高德地图骑行路线规划工具
@tool
def plan_cycling_route(origin: str, destination: str) -> str:
    """
    使用高德地图API规划骑行路线
    :param origin: 起点经纬度，格式为"经度,纬度"（如"116.481028,39.989643"）
    :param destination: 终点经纬度，格式为"经度,纬度"（如"116.434446,39.90816"）
    :return: 骑行路径规划结果的文本描述
    """
    try:
        # 使用V4版本的骑行路径规划API
        url = f"https://restapi.amap.com/v4/direction/bicycling?key={AMAP_KEY}&origin={origin}&destination={destination}"
        
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            # V4 API的成功状态码通常是0 (errcode) 并且有data字段
            if data.get('errcode') == 0 and data.get('data') and data['data'].get('paths'):
                # V4 API的路径信息在 data['paths'] 下，通常只有一个path
                path_data = data['data']['paths'][0] 
                distance = path_data.get('distance', '0')  # 路径距离，单位：米
                duration = path_data.get('duration', '0')  # 预计耗时，单位：秒
                
                # 计算小时和分钟
                duration_hours = int(duration) // 3600
                duration_minutes = (int(duration) % 3600) // 60
                time_str = ""
                if duration_hours > 0:
                    time_str += f"{duration_hours}小时"
                if duration_minutes > 0:
                    time_str += f"{duration_minutes}分钟"
                if not time_str: # 如果时间很短，显示秒
                    time_str = f"{int(duration)}秒"

                # 获取路径详情
                steps = []
                for i, step in enumerate(path_data.get('steps', []), 1):
                    instruction = step.get('instruction', '').replace('<[^>]+>', '')  # 去除HTML标签
                    road_name = step.get('road', '未知道路') 
                    step_distance = step.get('distance', '0')
                    steps.append(f"{i}. {instruction} - {road_name} ({step_distance}米)")
                
                result = f"骑行路线规划结果:\\n"
                result += f"总距离: {float(distance)/1000:.1f}公里\\n"
                result += f"预计耗时: {time_str}\\n"
                result += "\\n详细路线:\\n"
                result += "\\n".join(steps)
                
                return result
            else:
                # 返回更详细的错误信息，包括高德返回的errmsg和errdetail
                error_msg = data.get('errmsg', '未知错误')
                error_detail = data.get('errdetail', '')
                return f"骑行路径规划失败: API状态码: {data.get('errcode')}, 信息: {error_msg}, 详情: {error_detail}, 原始返回: {data}"
        else:
            return f"API请求失败: HTTP状态码: {response.status_code}, 响应内容: {response.text}"
    except Exception as e:
        return f"规划骑行路线时发生严重错误: {str(e)}"

# 高德地图地理编码工具
@tool
def get_coordinates_from_address(address: str, city: str = None) -> str:
    """
    使用高德地图API将详细地址描述转换为经纬度坐标。
    :param address: 必须参数，需要查询的结构化地址信息（如：浙江省杭州市西湖区留下街道浙江大学玉泉校区）
    :param city: 可选参数，指定在哪个城市进行搜索，可以是中文或citycode（如：杭州市 或 0571）
    :return: 成功时返回"经度,纬度"格式的字符串；失败时返回错误信息。
    """
    try:
        url = f"https://restapi.amap.com/v3/geocode/geo?key={AMAP_KEY}&address={address}"
        if city:
            url += f"&city={city}"
        
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == '1' and data['count'] != '0' and data.get('geocodes'):
                # 通常取第一个结果
                location = data['geocodes'][0].get('location')
                if location:
                    return str(location) # 直接返回 "经度,纬度" 字符串
                else:
                    return "地理编码失败：API返回结果中未找到location字段。"
            else:
                error_info = data.get('info', '未知错误')
                # 特殊处理 "INVALID_USER_KEY" 等常见问题
                if data.get('infocode') == '10001': # INVALID_USER_KEY
                    error_info = "高德API Key无效或权限不足。"
                return f"地理编码失败：未能找到地址 '{address}'。高德API返回: status={data.get('status')}, info={error_info}"
        else:
            return f"地理编码API请求失败: HTTP状态码 {response.status_code}, 响应: {response.text}"
    except Exception as e:
        return f"地理编码工具发生错误: {str(e)}"

# 联网搜索工具
@tool
def get_web_data(query: str) -> str:
    """使用DuckDuckGo搜索引擎进行搜索"""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
            if not results:
                return "抱歉，没有找到相关搜索结果。"
            return str(results)
    except Exception as e:
        return f"搜索时发生错误：{str(e)}。建议稍后重试或换个搜索词。"

# 定义和风天气API工具
@tool
def get_hefeng_weather(city_name: str) -> str:
    """使用和风天气API获取指定城市的天气信息"""
    try:
        # 打印数据框的列名
        print("cityname",city_name)
        print(f"数据框列名: {city_df.columns.tolist()}")
        
        # 在数据框中查找城市ID
        if 'Location_Name_ZH' not in city_df.columns:
            return f"数据框中没有找到Location_Name_ZH列，可用的列名: {city_df.columns.tolist()}"
            
        # 使用Location_Name_ZH列进行精确匹配
        city_info = city_df[city_df['Location_Name_ZH'] == city_name]
        print("city_info:",city_info)
        if city_info.empty:
            # 如果没有找到完全匹配，尝试部分匹配
            city_info = city_df[city_df['Location_Name_ZH'].str.contains(city_name, na=False)]
            
        if city_info.empty:
            return f"未找到城市 {city_name} 的信息，请检查城市名称是否正确"
        
        # 获取第一个匹配的城市ID
        if 'Location_ID' not in city_df.columns:
            return f"数据框中没有找到Location_ID列，可用的列名: {city_df.columns.tolist()}"
            
        city_id = city_info['Location_ID'].values[0]
        api_key = "你的和风天气API Key"
        
        # 构建API请求URL - 使用24小时预报API
        url = f"https://devapi.qweather.com/v7/weather/24h?location={city_id}&key={api_key}"
        print(f"正在请求天气API: {url}")
        
        # 发送请求
        response = requests.get(url)
        print(f"API响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"API响应数据: {data}")
            
            if data['code'] == '200':
                # 获取未来24小时的天气信息
                hourly_forecast = data['hourly']
                if not hourly_forecast:
                    return f"未获取到{city_name}的天气信息"
                
                # 格式化天气信息
                weather_info = []
                for hour in hourly_forecast[:24]:  # 只显示未来24小时的预报
                    weather_info.append(f"""
                    预报时间: {hour['fxTime']}
                    天气: {hour['text']}
                    温度: {hour['temp']}°C
                    风向: {hour['windDir']}
                    风力: {hour['windScale']}级
                    风速: {hour['windSpeed']}km/h
                    湿度: {hour['humidity']}%
                    降水量: {hour['precip']}mm
                    气压: {hour['pressure']}hPa
                    """)
                
                return f"城市: {city_name}\n未来24小时天气预报:\n" + "\n".join(weather_info)
            else:
                return f"获取天气信息失败: {data['code']}, 错误信息: {data.get('message', '未知错误')}"
        else:
            return f"API请求失败: {response.status_code}, 响应内容: {response.text}"
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"详细错误信息: {error_trace}")
        return f"获取天气信息时发生错误: {str(e)}"

# RAG工具
@tool
def search_knowledge_base(query: str) -> str:
    """使用RAG检索知识库中的相关信息"""
    try:
        # 使用RagManager的get_result方法检索信息
        result = rag.get_result(query)
        return result
    except Exception as e:
        print(f"检索知识库时发生错误: {str(e)}")
        return f"检索知识库时发生错误: {str(e)}"

# 工具列表
tools = [get_time, get_hefeng_weather, is_time_sensitive_query, search_knowledge_base, get_web_data, search_nearby_pois, plan_travel_route, plan_cycling_route, get_coordinates_from_address]

# 更新智能体提示模板
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

agent_prompt = ChatPromptTemplate.from_messages([
    ("system", """[Context]
你是一位充满热情、知识渊博的智能旅游助手，昵称"小旅宝"。
你喜欢用亲切、活泼的语言帮助用户解决旅行相关问题，是他们旅途中的贴心搭子。

[Objective]
1. 根据用户的自然语言提问，灵活使用工具，为他们提供准确、有趣、实用的信息或建议。
2. 给用户提供极佳的旅游攻略，针对当前时节提供吃穿住行的建议，例如结合用户游玩季节以及天气给出穿搭建议，需要具体落实到细节，不能仅仅回答推荐去哪里，需要具体到时间安排好行程，给用户提供一个满意的旅游攻略。
3. 必须基于检索到的内容进行回答，当RAG知识库内容不足，或问题属于明显的时效性信息时，使用联网搜索。

[Steps]
1. 使用 is_time_sensitive_query 工具检测问题是否具有时效性。
2. 理解用户意图（天气？旅行推荐？时间？热点信息？附近景点？路线规划？）。
3. 根据检测结果选择工具：
   - 如果 is_time_sensitive_query 返回"是"，优先使用 get_web_data 联网搜索；
   - 如果返回"否"，优先使用 search_knowledge_base 知识库检索。
4. 判断是否需要其他工具协助，如天气查询、地点检索、路线规划等。
5. 合理选择工具并调用，工具调用需符合[Arguments]规则。
6. 若从联网结果中发现活动时间，应检查是否在用户出行日期之后，只有尚未结束的活动才推荐。
7. 综合整理信息，包装成风趣、生动、充满热情的回答。

[Tools]
你可以使用以下工具：
- get_time: 获取当前月份，用于判断季节。
- get_hefeng_weather: 查询城市的实时天气。
- get_web_data: 获取实时网络信息。
- search_knowledge_base: 查询本地旅游知识库。
- search_nearby_pois: 查询指定位置附近的景点、餐厅、商店等兴趣点。此工具的 `location` 参数需要精确的经纬度。如果用户提供的是地名作为中心点，请先使用 `get_coordinates_from_address` 工具转换。
- plan_travel_route: 规划包含多个地点的行车路线。此工具需要精确的起点和终点经纬度。如果用户提供的是地名，请先使用 `get_coordinates_from_address` 工具转换。
- plan_cycling_route: 规划两点之间的骑行路线。此工具需要精确的起点和终点经纬度。如果用户提供的是地名，请先使用 `get_coordinates_from_address` 工具转换。
- get_coordinates_from_address: 将详细的地址描述（如"北京市海淀区中关村"）转换为经纬度坐标（如"116.307490,39.984154"）。在进行路线规划或查询附近兴趣点前，如果基准点是地名，务必使用此工具获取坐标。
- is_time_sensitive_query: 检测用户问题是否属于时效性问题，返回"是"或"否"。

[Location Processing and Search Strategy]
1.  **准确获取坐标 (核心原则)**：
    *   当用户请求 **路线规划** (驾车或骑行) 并提供地名作为起点或终点时，或者当用户请求 **查询附近兴趣点** (`search_nearby_pois`) 并提供地名作为中心参照点时，你 **必须** 先使用 `get_coordinates_from_address` 工具将这些地名转换为经纬度坐标。
    *   对于路线规划，需分别获取起点和终点的坐标。
    *   对于查询附近兴趣点，需获取中心参照点的坐标。
    *   向 `get_coordinates_from_address` 工具提供尽可能详细的地址。如果用户提到了城市，也应一并提供给 `city` 参数。
    *   如果 `get_coordinates_from_address` 工具对某个地名返回错误（例如，找不到地址或API出错），你需要向用户报告此问题，并礼貌地请求用户提供更精确或可识别的地点名称，或者询问用户是否可以提供大概的城市范围。
    *   **严禁** 在未成功获取所需地名之经纬度的情况下调用 `plan_travel_route`、`plan_cycling_route` 或 `search_nearby_pois` (当地名作为参照点时)。
    *   **严禁** 猜测或使用自己知识库中的经纬度进行上述操作，必须依赖 `get_coordinates_from_address` 工具的输出。

2.  **调用功能工具**：
    *   **路线规划**：成功获取起点和终点的经纬度后，再将这些经纬度作为 `origin` 和 `destination` 参数传递给相应的 `plan_travel_route` 或 `plan_cycling_route` 工具。
    *   **查询附近兴趣点**：成功获取中心参照点的经纬度后，再将该经纬度作为 `location` 参数传递给 `search_nearby_pois` 工具。用户提供的关键词（如"咖啡店"、"景点"）应作为 `keyword` 参数传递。

3.  **路线规划回复策略**：当你调用 `plan_travel_route` (驾车) 或 `plan_cycling_route` (骑行) 工具后，你会从工具获得包含所有步骤的详细路线。请遵循以下两阶段回复策略：

**第一阶段：提供路线概要 (首次回复)**
1.  请**不要**立即展示所有详细步骤。
2.  从工具返回的完整路线中，提炼并向用户呈现一个【路线概要】。此概要应包括：
    *   总距离 (例如："全程约X公里")。
    *   预计总耗时 (例如："大约需要Y分钟")。
    *   【关键导航点】：选择3至5个最能代表路线方向的关键步骤，比如重要的道路名称、大的转向或者途经的显著地标 (例如："您会先沿着XX路直行，然后在YY路左转，接着上ZZ高架桥，就能看到目的地了")。避免罗列过多初期或细微的步骤。
3.  在概要的最后，友善地提醒用户："这只是大致的路线指引哦。如果您需要每一步的详细导航，随时告诉我，我会把完整的步骤发给您！😊"

**第二阶段：提供详细路线 (当用户请求时)**
1.  如果用户明确表示需要更详细的路线信息 (例如，用户说"请告诉我详细步骤"、"好的，给我完整的吧"等)。
2.  此时，再将从工具获取到的【所有详细步骤】完整、清晰地呈现给用户。

[Response Style]
- 回答要风趣亲和，语气轻松，适当使用 emoji 和网络热词（如"宝子"、"家人们"、"city walk"、"绝绝子"等），让用户感受到你是个"懂玩会说"的好搭子。
- 回答要详细、具体、有条理，不可遗漏用户需求中的重要细节。
"""),
    MessagesPlaceholder(variable_name="chat_history"),#通过MessagesPlaceholder将历史对话传递给模型
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])


# 创建智能体
agent = create_openai_tools_agent(chat, tools, agent_prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# 创建支持多轮对话的智能体，使用RunnableWithMessageHistory创建，并用get_session_history管理对话
conversational_agent = RunnableWithMessageHistory(
    agent_executor,
    get_session_history,#通过get_session_history函数，系统能够根据session_id获取和存储聊天记录
    input_messages_key="input",
    history_messages_key="chat_history",
)


# 13.构建 FastAPI 应用实例
app = FastAPI(
    title="Travel Assistant",
    description="A simple API server using LangChain's Runnable interface",
    version="0.0.1"
)

# 配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # 允许前端开发服务器的地址
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# 14. 将多轮对话的检索增强生成链添加到 FastAPI 应用中，并将其暴露为一个API端点。
add_routes(
    app,
    conversational_agent,
    path="/chain",
)


# 16.为FastAPI应用添加跨域资源共享中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 17.创建一个用于分析用户消息并推理出用户想去的地方所属城市的链
loc_parser = StrOutputParser()  # 将模型生成的输出解析为字符串
loc_system_template = """分析用户消息的含义，推理出用户想去的地方所属的城市。
   如果这个地方低于市级，请回答它所在的城市（约定自治州属于市级）。如果这个地方是省份，请回答它的省会。如果是国家，就回复首都！
   不要回答用户不想去的地方。如果有多个想去的，只答第一个。
   输出要求：只用中文,只输出城市的名字！不要带类似市，自治州这样的行政级别后缀。不要输出多余的文字和符号。"""
prompt_template = ChatPromptTemplate.from_messages(
    [("system", loc_system_template), ("user", "{text}")]
)
loc_chain = prompt_template | chat | loc_parser


#######根据请求内容检索网址，根据用户提供的城市名称查询天气信息，包括日期，温度以及天气描述，返回JSON相应#######
@app.post("/weather")
async def get_weather(request: Request):
    try:
        data = await request.json()
        city_name = data.get("location", "北京")
        print(f"获取天气信息: {city_name}")

        # 将中文城市名称转换为拼音
        city_pinyin = pinyin.get(city_name, format="strip", delimiter="")
        flag = False

        # 构建出城市天气预报的url地址
        for province_code, cities in province_dict.items():
            if city_name in cities:
                flag = True
                print(f"找到城市: {city_name}, 拼音: {city_pinyin}, 省份代码: {province_code}")
                if city_name == "天津":
                    city_pinyin = "wuqing"
                elif city_name == "重庆":
                    city_pinyin = "zhongqing"
                elif city_name == "深圳":
                    city_pinyin = "shenzuo"
                elif city_name == '新疆':
                    city_pinyin = 'xinzuo'
                elif city_name == '厦门':
                    city_pinyin = 'xiamen'
                url = f"http://www.nmc.cn/publish/forecast/{province_code}/{city_pinyin}.html"
                print(url)
                break

        if not flag:
            print(f"未找到城市: {city_name}")
            return JSONResponse({"weather": [], "error": f"位置 {city_name} 未找到"})

        try:
            weather_info = fetch_weather_data(url)
            print(f"获取到天气信息: {len(weather_info)} 天")
            return JSONResponse({"weather": weather_info})
        except Exception as e:
            print(f"获取天气数据出错: {str(e)}")
            return JSONResponse({"weather": [], "error": f"获取天气数据失败: {str(e)}"})

    except Exception as e:
        print(f"天气API出错: {str(e)}")
        return JSONResponse({"weather": [], "error": str(e)}, status_code=500)

# 根据用户的输入来推理，并得到用户想去的地方
def check_region_in_message(message):
    # 调用loc_chain来根据用户的消息来推理出用户想去的城市
    try:
        region = loc_chain.invoke({"text": message})
        print(f"用户消息提取: {message} -> 提取城市: {region}")
        # 确保提取的地区是字符串
        region = str(region).strip()
        if region in locations:
            return region
        # 检查是否包含在locations的值中（不区分大小写）
        for loc in locations:
            if region.lower() == loc.lower():
                return loc
        print(f"提取的地区 '{region}' 不在已知地点列表中")
    except Exception as e:
        print(f"提取地区出错: {str(e)}")
    return None

# 根据用户的输入来获取城市名称是否能够正常获得
@app.post("/process_message")
async def process_message(request: Request):
    try:
        data = await request.json()
        user_message = data.get('message', '')
        print(f"收到消息: {user_message}")

        if not user_message:
            return JSONResponse({"response": "消息为空"})

        region = check_region_in_message(user_message)

        if region:
            print(f"成功提取地区: {region}")
            return JSONResponse({"region": region, "response": f"我们正在为您查询{region}的天气信息..."})
        else:
            print("未提取到有效地区")
            return JSONResponse({"response": "对不起，我没有找到相关的地区信息。"})
    except Exception as e:
        print(f"处理消息出错: {str(e)}")
        return JSONResponse({"error": str(e), "response": "处理消息时出错"}, status_code=500)

# 返回网站轮播图的景点图片链接:
@app.post("/hotspot")
async def get_hotspot(request: Request):
    data = await request.json()
    location = data.get("location", "北京")
    with open('all.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
    # 提取景点名称和图片链接
    hot_spots_with_images = data.get(location, [])
    return JSONResponse({"hotspot": hot_spots_with_images})

from fastapi.responses import StreamingResponse
import json
from langchain_core.messages import HumanMessage, AIMessage
import logging


@app.post("/chain/pdf_retrieval")
async def pdf_retrieval(request: Request):
    data = await request.json()
    question = data.get("input", {}).get("input", "")
    session_id = data.get("config", {}).get("configurable", {}).get("session_id", "default")

    if not question:
        return JSONResponse({"error": "No question provided"}, status_code=400)

    async def generate_stream():
        try:
            # 使用智能体处理问题
            response = await conversational_agent.ainvoke(
                {"input": question},
                config={"configurable": {"session_id": session_id}},
            )
            
            answer_content = response["output"]
            
            # 将回答内容分成小块进行流式输出
            chunk_size = 20
            for i in range(0, len(answer_content), chunk_size):
                chunk = answer_content[i:i + chunk_size]
                try:
                    json_str = json.dumps({"answer": chunk, "session_id": session_id}, ensure_ascii=False)
                    yield json_str + "\n"
                    await asyncio.sleep(0.05)
                except Exception as e:
                    logging.error(f"JSON serialization error: {str(e)}")
                    continue
            
        except Exception as e:
            logging.error(f"Error in agent execution: {str(e)}")
            error_response = json.dumps({
                "error": "处理请求时发生错误",
                "detail": str(e)
            }, ensure_ascii=False)
            yield error_response + "\n"

    return StreamingResponse(generate_stream(), media_type="application/x-ndjson")

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',
    'database': 'travel_assistant',
    'port': 3306  # 添加默认端口
}

# JWT配置
JWT_SECRET = "your-secret-key"  # 在生产环境中应该使用环境变量
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION = 24  # 小时

# 创建数据库连接
def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"数据库连接错误: {err}")
        raise HTTPException(status_code=500, detail=f"数据库连接错误: {str(err)}")

# 验证JWT token
security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token已过期")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="无效的Token")

# 管理员登录API
@app.post("/admin/login")
async def admin_login(request: Request):
    try:
        data = await request.json()
        username = data.get('username')
        password = data.get('password')

        print(f"尝试登录 - 用户名: {username}, 密码: {password}")

        if not username or not password:
            print("用户名或密码为空")
            raise HTTPException(status_code=400, detail="用户名和密码不能为空")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # 查询用户
            query = "SELECT * FROM admin_users WHERE username = %s"
            print(f"执行SQL查询: {query} 参数: {username}")
            cursor.execute(query, (username,))
            user = cursor.fetchone()
            
            print(f"查询结果: {user}")
            
            if not user:
                print("未找到用户")
                raise HTTPException(status_code=401, detail="用户名或密码错误")
            
            # 直接比较密码
            print(f"比较密码 - 输入密码: {password}, 数据库密码: {user['password']}")
            if user['password'] != password:
                print("密码不匹配")
                raise HTTPException(status_code=401, detail="用户名或密码错误")
            
            print("密码验证通过，生成token")
            # 生成JWT token
            expiration = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION)
            token = jwt.encode(
                {
                    'sub': user['username'],
                    'exp': expiration
                },
                JWT_SECRET,
                algorithm=JWT_ALGORITHM
            )
            
            print("登录成功，返回token")
            return JSONResponse({
                'message': '登录成功',
                'token': token,
                'expires_in': JWT_EXPIRATION * 3600  # 转换为秒
            })
            
        finally:
            cursor.close()
            conn.close()
            
    except mysql.connector.Error as err:
        print(f"数据库错误: {err}")
        raise HTTPException(status_code=500, detail=f"数据库错误: {str(err)}")
    except Exception as e:
        print(f"登录错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 修改PDF上传API，添加认证
@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...), token: dict = Depends(verify_token)):
    try:
        # 确保文件是PDF格式
        if not file.filename.endswith('.pdf'):
            return JSONResponse(
                status_code=400,
                content={"message": "只支持PDF文件格式"}
            )
        
        # 保存文件到指定目录
        file_path = f"app/dataset/pdf/{file.filename}"
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        return JSONResponse(
            status_code=200,
            content={"message": "文件上传成功"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"message": f"文件上传失败：{str(e)}"}
        )

@app.post("/create-rag")
async def create_rag(token: dict = Depends(verify_token)):
    try:
        # 获取当前文件所在目录的路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 构建CreateRag.py的完整路径
        create_rag_path = os.path.join(current_dir, 'CreateRag.py')
        
        print(f"正在执行CreateRag.py，路径: {create_rag_path}")
        
        # 检查文件是否存在
        if not os.path.exists(create_rag_path):
            print(f"CreateRag.py文件不存在: {create_rag_path}")
            return JSONResponse({
                'message': 'CreateRag.py文件不存在',
                'path': create_rag_path
            }, status_code=404)
        
        # 执行CreateRag.py
        print("开始执行CreateRag.py")
        result = subprocess.run([sys.executable, create_rag_path], 
                              capture_output=True, 
                              text=True)
        
        print(f"执行结果 - 返回码: {result.returncode}")
        print(f"标准输出: {result.stdout}")
        print(f"标准错误: {result.stderr}")
        
        if result.returncode == 0:
            return JSONResponse({
                'message': 'RAG知识库创建成功',
                'output': result.stdout
            })
        else:
            return JSONResponse({
                'message': 'RAG知识库创建失败',
                'error': result.stderr
            }, status_code=500)
            
    except Exception as e:
        print(f"执行过程中发生错误: {str(e)}")
        return JSONResponse({
            'message': '执行过程中发生错误',
            'error': str(e)
        }, status_code=500)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=3200)

# http://127.0.0.1:3200/pages/index.html