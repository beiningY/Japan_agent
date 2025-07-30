import requests
import json
def test_upload_files():
    BASE_URL = "http://localhost:5001/api/upload"  
    file_path = 'data/raw_data/log/2025_06_12.txt'  # 替换成测试文件

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

if __name__ == "__main__":
    test_upload_files()
    test_get_operation_logs()