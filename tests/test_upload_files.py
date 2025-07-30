import requests
import json
BASE_URL = "http://localhost:5001/api/upload"  
file_path = 'data/raw_data/log/2025_06_12.txt'  # 替换成测试文件

with open(file_path, 'rb') as f:
    files = {'file': f}
    response = requests.post(BASE_URL, files=files)
print("状态码:", response.status_code)
print("返回值:", response.json())