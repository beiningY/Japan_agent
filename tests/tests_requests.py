import requests
import json
import uuid
import sseclient
import requests
from urllib.parse import urlencode

def test_upload_files():
    BASE_URL = "http://localhost:5001/api/upload"  
    file_path = 'data/raw_data/log/2025_06_12.txt'  

    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(BASE_URL, files=files)
    print("状态码:", response.status_code)
    print("返回值:", response.json())


def test_get_operation_logs():
    BASE_URL = "http://localhost:5000/api/get_files"
    payload = {
        "type": "操作日志",
        "filenames": ["2025_07_07.txt", "2025_07_08.txt"]
    }
    response = requests.post(BASE_URL, json=payload)
    print("操作日志测试结果:")
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))


def test_run_query():
    BASE_URL = "http://localhost:5001/api/run_query"
    payload = {'query': '日本陆上养殖技术', 'agent_type': 'japan'}

    try:
        # 发送 POST 请求
        response = requests.post(BASE_URL, json=payload)

        # 检查响应状态
        if response.status_code == 200:
            print("成功返回结果：")
            print(response.json())
        else:
            print("请求失败，状态码: {response.status_code}")
            print(response.json())

    except Exception as e:
        print(f"请求出错: {e}")
def test_get_kb_list():
    url = "http://localhost:5001/api/get_knowledge_base_list"
    params = {
        "kb_ids": "25241d69-33fd-465d-8fd1-18d34865248c,cede3e0b-6447-4418-9c80-97129710beb5"
    }
    response = requests.get(url, params=params)
    print(response.json())


def test_sse():
    url = "http://localhost:5001/api/test_stream"
    params = {
        "agent_type": "japan",
        "query": "如何调整ph值"
    }

    print("正在测试SSE流...")
    with requests.get(url, params=params, stream=True) as resp:
        print(f"响应状态码: {resp.status_code}")
        print(f"响应头: {dict(resp.headers)}")
        print("-" * 50)
        
        for line in resp.iter_lines(decode_unicode=True):
            if line:  
                print(f"收到数据: {line}")
                # 如果是SSE格式，提取数据内容
                if line.startswith("data: "):
                    data_content = line[6:]
                    print(f"数据内容: {data_content}")
                print("-" * 30)


def connect_sse():
    base_url = "http://localhost:5001/stream"
    session_id = str(uuid.uuid4())
    query = "贷款有哪些类型？"
    agent_type = "bank"
    params = {
        'session_id': session_id,
        'query': query,
        'agent_type': agent_type
    }
    
    url = f"{base_url}?{urlencode(params)}"
    print(f"连接URL: {url}")
    try:
        # 使用sseclient库连接SSE流
        # sseclient需要传入URL，它会自己处理请求
        client = sseclient.SSEClient(url)
        
        print("已连接到 SSE 流，等待消息...")
        for event in client.events():
            print(f"收到消息: {event.data}")
            # 可以解析JSON数据
            try:
                data = json.loads(event.data)
                print(f"解析后的数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
            except json.JSONDecodeError:
                print("数据不是有效的JSON格式")
            
    except requests.exceptions.RequestException as e:
        print(f"请求错误: {e}")
    except Exception as e:
        print(f"连接SSE时发生错误: {e}")
        # 如果sseclient失败，尝试直接读取
        print("尝试直接读取响应...")
        try:
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                for line in response.iter_lines(decode_unicode=True):
                    if line:
                        print(f"原始数据: {line}")
        except Exception as e2:
            print(f"直接读取也失败: {e2}")


def test_simple_sse():
    """简单的SSE测试，不使用sseclient库"""
    base_url = "http://localhost:5001/stream"
    session_id = str(uuid.uuid4())
    query = "贷款有哪些类型？"
    agent_type = "bank"
    params = {
        'session_id': session_id,
        'query': query,
        'agent_type': agent_type
    }
    
    url = f"{base_url}?{urlencode(params)}"
    print(f"连接URL: {url}")
    
    try:
        response = requests.get(url, stream=True)
        print(f"响应状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("开始接收SSE数据...")
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    print(f"收到数据: {line}")
        else:
            print(f"请求失败: {response.text}")
            
    except Exception as e:
        print(f"测试失败: {e}")


if __name__ == "__main__":
    #test_upload_files()
    #test_get_operation_logs()
    #test_run_query()
    #test_get_kb_list()
    #test_sse()
    #test_simple_sse()
    connect_sse()