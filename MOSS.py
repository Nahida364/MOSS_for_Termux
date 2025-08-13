import requests
import json
import os
import subprocess
import sys
import re
from datetime import datetime

NASA_API_KEY = "dYhYcQOMYEcBQRf633t1LVhtQW7G8nQdKylipgiS"
SENIVERSE_API_KEY = "SD7AILROlMhU3fBZc"

def play_audio(filename):
    """播放音频文件"""
    if os.path.exists(filename):
        try:
            subprocess.run(["termux-media-player", "play", filename])
        except Exception as e:
            print(f"播放音频失败: {e}")

def save_message(user_input, ai_response):
    """保存对话记录到msg.txt"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("msg.txt", "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] 用户: {user_input}\n")
        f.write(f"[{timestamp}] MOSS: {ai_response}\n\n")

def load_roles():
    """从role.txt加载角色配置"""
    roles = {}
    if os.path.exists("role.txt"):
        with open("role.txt", "r", encoding="utf-8") as f:
            for line in f:
                if "|" in line:
                    parts = line.strip().split("|", 3)
                    if len(parts) >= 4:
                        role_name = parts[0]
                        system_content = parts[1]
                        params = parts[2].split(",")
                        if len(params) == 3:
                            roles[role_name] = {
                                "system": system_content,
                                "temperature": float(params[0]),
                                "frequency_penalty": float(params[1]),
                                "max_tokens": int(params[2])
                            }
    return roles

def save_roles(roles):
    """保存角色配置到role.txt"""
    with open("role.txt", "w", encoding="utf-8") as f:
        for role_name, config in roles.items():
            params = f"{config['temperature']},{config['frequency_penalty']},{config['max_tokens']}"
            f.write(f"{role_name}|{config['system']}|{params}\n")

def get_streaming_response(api_key, model, messages, temperature=1.0, frequency_penalty=0.0, max_tokens=8192):
    """处理流式API响应"""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": messages,
        "stream": True,
        "temperature": temperature,
        "frequency_penalty": frequency_penalty,
        "max_tokens": max_tokens
    }
    
    response = requests.post(url, headers=headers, json=data, stream=True)
    full_response = ""
    
    if response.status_code != 200:
        print(f"错误: {response.status_code} - {response.text}")
        return None
    
    print("MOSS: ", end="", flush=True)
    for line in response.iter_lines():
        if line:
            decoded_line = line.decode('utf-8')
            if decoded_line.startswith("data: "):
                json_data = decoded_line[6:]
                if json_data == "[DONE]":
                    continue
                
                try:
                    event = json.loads(json_data)
                    if "choices" in event and event["choices"]:
                        chunk = event["choices"][0]["delta"].get("content", "")
                        if chunk:
                            print(chunk, end="", flush=True)
                            full_response += chunk
                except json.JSONDecodeError:
                    continue
    
    print("\n")
    return full_response

def get_non_streaming_response(api_key, model, messages, temperature=1.0, frequency_penalty=0.0, max_tokens=8192):
    """处理非流式API响应"""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": messages,
        "stream": False,
        "temperature": temperature,
        "frequency_penalty": frequency_penalty,
        "max_tokens": max_tokens
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code != 200:
        print(f"错误: {response.status_code} - {response.text}")
        return None
    
    result = response.json()
    reply = result["choices"][0]["message"]["content"]
    print(f"MOSS: {reply}\n")
    return reply

def get_nasa_apod():
    """获取NASA每日天文图片"""
    if NASA_API_KEY == "":
        print("在代码中设置APIKEY")
        return
    
    url = f"https://api.nasa.gov/planetary/apod?api_key={NASA_API_KEY}"
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"获取NASA数据失败: {response.status_code}")
        return
    
    data = response.json()
    
    print("\n==== NASA 每日天文图片 ====")
    print(f"标题: {data.get('title', '无标题')}")
    print(f"日期: {data.get('date', '未知日期')}")
    print(f"说明: {data.get('explanation', '无说明')}")
    
    # 创建保存目录
    save_dir = "//storage/emulated/0/Pictures/NASA"
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    # 下载图片
    if 'hdurl' in data:
        image_url = data['hdurl']
    elif 'url' in data:
        image_url = data['url']
    else:
        print("未找到图片URL")
        return
    
    try:
        image_response = requests.get(image_url)
        if image_response.status_code == 200:
            filename = image_url.split("/")[-1]
            
            filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
            save_path = os.path.join(save_dir, filename)
            
            with open(save_path, "wb") as f:
                f.write(image_response.content)
            print(f"图片已保存至: {save_path}")
        else:
            print(f"下载图片失败: {image_response.status_code}")
    except Exception as e:
        print(f"下载图片时出错: {e}")

def get_weather(city):
    """获取城市天气信息"""
    if SENIVERSE_API_KEY == "":
        print("在代码中设置SENIVERSE_API_KEY")
        return
    
    url = f"https://api.seniverse.com/v3/weather/now.json?key={SENIVERSE_API_KEY}&location={city}&language=zh-Hans&unit=c"
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"获取天气数据失败: {response.status_code}")
        return
    
    data = response.json()
    
    if 'results' in data and data['results']:
        result = data['results'][0]
        location = result['location']['name']
        weather = result['now']['text']
        temperature = result['now']['temperature']
        last_update = result['last_update']
        
        print(f"\n==== {location} 天气 ====")
        print(f"天气状况: {weather}")
        print(f"温度: {temperature}°C")
        print(f"更新时间: {last_update}")
    else:
        print("未找到该城市的天气信息")

def main():
    print("\n作者是小吉祥草王哒~QQ号3921536252\n")
    # 获取API Key
    api_key = input("输入deepseek官方APIkey：").strip()
    
    # 播放欢迎音频
    play_audio("我是载人轨道空间站控制系统.wav")
    
    # 初始化设置
    current_system = "你是《流浪地球》中的550W，又叫MOSS，请以MOSS的风格与用户对话，不超过128字"
    model = "deepseek-chat"
    stream_enabled = True
    temperature = 1.0
    frequency_penalty = 0.0
    max_tokens = 8192
    messages = [
        {"role": "system", "content": current_system}
    ]
    
    # 加载角色配置
    roles = load_roles()
    
    print("\n对话已就绪（输入/help查看命令帮助）")
    
    while True:
        user_input = input("对话：").strip()
        
        # 处理命令
        if user_input == "/exit":
            print("对话结束")
            break
            
        elif user_input == "/clear":
            messages = [{"role": "system", "content": current_system}]
            print("对话历史已清空\n")
            continue
            
        elif user_input == "/msg":
            if os.path.exists("msg.txt"):
                print("\n==== 对话记录 ====")
                with open("msg.txt", "r", encoding="utf-8") as f:
                    print(f.read())
            else:
                print("暂无对话记录\n")
            continue
            
        elif user_input.startswith("/system "):
            new_system = user_input[8:].strip()
            current_system = new_system
            messages = [{"role": "system", "content": current_system}]
            print(f"系统设定已更新: {new_system}\n")
            continue
            
        elif user_input.startswith("/model "):
            new_model = user_input[7:].strip()
            model = new_model
            print(f"模型已切换为: {model}\n")
            continue
            
        elif user_input.startswith("/stream "):
            stream_arg = user_input[8:].strip()
            if stream_arg == "1":
                stream_enabled = True
                print("已启用流式输出\n")
            elif stream_arg == "0":
                stream_enabled = False
                print("已禁用流式输出\n")
            else:
                print("无效参数，使用 /stream 0 或 /stream 1\n")
            continue
        
        elif user_input.startswith("/add "):
            parts = user_input[5:].split(" ", 1)
            if len(parts) < 2:
                print("格式错误，使用 /add 角色名 设定内容")
                continue
            role_name = parts[0].strip()
            role_content = parts[1].strip()
            
            # 添加到角色配置
            roles[role_name] = {
                "system": role_content,
                "temperature": temperature,
                "frequency_penalty": frequency_penalty,
                "max_tokens": max_tokens
            }
            save_roles(roles)
            print(f"已添加角色 '{role_name}'\n")
            continue
            
        elif user_input.startswith("/role "):
            role_name = user_input[6:].strip()
            if role_name in roles:
                role_config = roles[role_name]
                current_system = role_config["system"]
                temperature = role_config["temperature"]
                frequency_penalty = role_config["frequency_penalty"]
                max_tokens = role_config["max_tokens"]
                
                messages = [{"role": "system", "content": current_system}]
                print(f"已切换到角色 '{role_name}'")
                print(f"系统设定: {current_system}")
                print(f"参数: temperature={temperature}, fp={frequency_penalty}, tokens={max_tokens}\n")
            else:
                print(f"未找到角色 '{role_name}'\n")
            continue
            
        elif user_input.startswith("/del "):
            role_name = user_input[5:].strip()
            if role_name in roles:
                del roles[role_name]
                save_roles(roles)
                print(f"已删除角色 '{role_name}'\n")
            else:
                print(f"未找到角色 '{role_name}'\n")
            continue
            
        elif user_input.startswith("/temp "):
            try:
                new_temp = float(user_input[6:].strip())
                temperature = new_temp
                print(f"temperature 已设置为: {temperature}\n")
            except ValueError:
                print("无效值，请输入数字\n")
            continue
            
        elif user_input.startswith("/fp "):
            try:
                new_fp = float(user_input[4:].strip())
                frequency_penalty = new_fp
                print(f"frequency_penalty 已设置为: {frequency_penalty}\n")
            except ValueError:
                print("无效值，请输入数字\n")
            continue
            
        elif user_input.startswith("/token "):
            try:
                new_token = int(user_input[7:].strip())
                max_tokens = new_token
                print(f"max_tokens 已设置为: {max_tokens}\n")
            except ValueError:
                print("无效值，请输入整数\n")
            continue
            
        elif user_input == "/nasa":
            get_nasa_apod()
            continue
            
        elif user_input.startswith("/weather "):
            city = user_input[9:].strip()
            if city:
                get_weather(city)
            else:
                print("请输入城市名\n")
            continue
            
        elif user_input == "/help":
            print("\n命令列表:")
            print("/exit      - 退出程序")
            print("/clear     - 清空对话历史")
            print("/msg       - 查看对话记录")
            print("/system [内容] - 设置临时角色设定\n例如/system 你是一个猫娘")
            print("/model [名称]  - 切换模型\n可选deepseek-chat,deepseek-reasoner")
            print("/stream [0/1]  - 开关流式输出")
            print("/add [角色名] [设定] - 添加自定义角色")
            print("/role [角色名]  - 切换自定义角色")
            print("/del [角色名]   - 删除自定义角色")
            print("/temp [值]     - 修改temperature值,0~2")
            print("/fp [值]       - 修改frequency_penalty值,-2~2")
            print("/token [值]    - 修改max_tokens值,最大8192")
            print("/nasa       - NASA每日天文")
            print("/weather [城市] - 获取城市天气信息\n")
            continue
        
        # 普通用户输入
        messages.append({"role": "user", "content": user_input})
        
        # 获取AI回复
        if stream_enabled:
            response = get_streaming_response(
                api_key, model, messages, 
                temperature, frequency_penalty, max_tokens
            )
        else:
            response = get_non_streaming_response(
                api_key, model, messages, 
                temperature, frequency_penalty, max_tokens
            )
        
        if response:
            messages.append({"role": "assistant", "content": response})
            # 保存对话记录
            save_message(user_input, response)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n程序已终止")
        sys.exit(0)
