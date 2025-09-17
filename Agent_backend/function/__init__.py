from bs4 import BeautifulSoup
import requests
import bs4
from langchain_text_splitters import RecursiveCharacterTextSplitter
import re
from langchain_community.document_loaders import WebBaseLoader




##################自定义函数###################
"""
加载+拆分
"""
def load_and_split(url):
    # 告诉BeautifulSoup 只解析 class 属性为 "7days day7 pull-right clearfix" 的 HTML 元素，忽略其他部分
    bs4_strainer = bs4.SoupStrainer(class_="7days day7 pull-right clearfix")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=100, add_start_index=True
    )
    loader = WebBaseLoader(
        web_paths=(url,),
        bs_kwargs={"parse_only": bs4_strainer},
    )
    docs = loader.load()
    print(text_splitter.split_documents(docs))
    return text_splitter.split_documents(docs)


#从某地区url提取天气信息
def fetch_weather_data(url):
    try:
        print(f"获取天气数据URL: {url}")
        response = requests.get(url, timeout=10)
        
        if not response.ok:
            print(f"获取天气页面失败: 状态码 {response.status_code}")
            return []
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 提取天气信息
        weather_info = []
        
        #找到日期标签，在soup对象中查找所有class属性为date的HTML元素，并将它们存储在days列表中
        days = soup.find_all(class_='date')
        if not days:
            print("未找到日期数据")
            return []
            
        #温度标签的class用正则表达式表示
        temp_pattern = re.compile(r'tmp tmp_lte_\w+')
        #找到所有的温度标签
        temperatures = soup.find_all(class_=temp_pattern)
        if not temperatures:
            print("未找到温度数据")
            return []
            
        #找到天气描述的标签
        descriptions = soup.find_all(class_='desc')
        if not descriptions:
            print("未找到天气描述数据")
            return []
            
        print(f"提取到数据: {len(days)}天, {len(temperatures)}个温度, {len(descriptions)}个描述")
        
        #整理列表
        ####################晚上生效###################
        ##如果 temperatures 列表的长度为 13，因为到了晚上就不会显示白天的温度了，则插入一个空的温度标签到列表的开头。
        if(len(temperatures)==13):
            print("检测到晚间数据格式，调整温度列表")
            new_element_html = "<div class='tmp tmp_lte_40'> </div>"
            new_element = BeautifulSoup(new_element_html, 'html.parser').div
            temperatures.insert(0, new_element)
        ####################晚上生效###################
        
        ##获取上午和下午的温度
        temperatures_l = [temperatures[i] for i in range(0, len(temperatures), 2)]
        temperatures_h = [temperatures[i] for i in range(1, len(temperatures), 2)]
        ##获取最上午和下午所对应的天气描述
        description_1 = [descriptions[i] for i in range(0, len(descriptions), 2)]
        description_2 = [descriptions[i] for i in range(1, len(descriptions), 2)]

        if len(days) == len(temperatures_l) == len(temperatures_h) == len(description_1) == len(description_2):
            print(f"数据匹配成功，处理{len(days)}天的天气信息")
            for day, temp_l, temp_h, desc1, desc2 in zip(days, temperatures_l, temperatures_h, description_1, description_2):
                try:
                    date = day.get_text(strip=True)
                    temperature_l = temp_l.get_text(strip=True)
                    temperature_h = temp_h.get_text(strip=True)
                    description1 = desc1.get_text(strip=True)
                    description2 = desc2.get_text(strip=True)
                    #上午和下午的天气描述如果是一样的
                    if(description1==description2):
                        weather_info.append(f"{date}: {temperature_l}~{temperature_h}, {description1}")
                    #上午和下午的天气描述不一样
                    else:
                        weather_info.append(f"{date}: {temperature_l}~{temperature_h}, {description1}转{description2}")
                except Exception as e:
                    print(f"处理单天天气数据出错: {e}")
        else:
            print(f"数据长度不匹配: 日期={len(days)}, 低温={len(temperatures_l)}, 高温={len(temperatures_h)}, 描述1={len(description_1)}, 描述2={len(description_2)}")
            # 尝试提取尽可能多的数据
            for i in range(min(len(days), len(temperatures_l), len(temperatures_h), len(description_1), len(description_2))):
                try:
                    date = days[i].get_text(strip=True)
                    temperature_l = temperatures_l[i].get_text(strip=True)
                    temperature_h = temperatures_h[i].get_text(strip=True)
                    description1 = description_1[i].get_text(strip=True)
                    description2 = description_2[i].get_text(strip=True)
                    
                    if(description1==description2):
                        weather_info.append(f"{date}: {temperature_l}~{temperature_h}, {description1}")
                    else:
                        weather_info.append(f"{date}: {temperature_l}~{temperature_h}, {description1}转{description2}")
                except Exception as e:
                    print(f"处理第{i+1}天天气数据出错: {e}")
                    
        print(f"成功提取{len(weather_info)}天的天气信息")
        return weather_info
        
    except Exception as e:
        print(f"提取天气数据失败: {e}")
        return []

