import requests
import json
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
    url = "http://localhost:5001/stream"
    with requests.get(url, stream=True) as response:
        if response.status_code != 200:
            print(f"Failed to connect, status code: {response.status_code}")
            return
        for line in response.iter_lines(decode_unicode=True):
            if line:
                print(f"收到的数据{line}")
        print(response.iter_lines(decode_unicode=True))



if __name__ == "__main__":
    #test_upload_files()
    #test_get_operation_logs()
    #test_run_query()
    #test_get_kb_list()
    test_sse()