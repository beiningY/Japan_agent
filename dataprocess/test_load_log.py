import requests
import json
BASE_URL = "http://localhost:5000/api/get_files"  

def test_get_operation_logs():
    payload = {
        "type": "操作日志",
        "filenames": ["2025_07_08.txt", "2025_07_09.txt"]
    }
    response = requests.post(BASE_URL, json=payload)
    print("操作日志测试结果:")
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    test_get_operation_logs()