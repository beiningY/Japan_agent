import requests
import json
import uuid
import sseclient
import requests
from urllib.parse import urlencode

def test_agent_config():
    url = "http://localhost:5001/sse/agent_config"
    response = requests.get(url)
    print(response.json())

def test_stream_qa():
    url = "http://localhost:5001/sse/stream_qa"
    config = {
            "mode": "auto",
            "rag": {
            "collection_name": "japan_shrimp",
            "topk_single": 5,
            "topk_multi": 5
            },
            "single": {
            "temperature": 0.4,
            "system_prompt": "你是一个领域专家，你的任务是根据用户的问题，结合增强检索后的相关知识，给出专业的回答。",
            "max_tokens": 4096
            },
            "roleplay": {
            "temperature": 0.4,
            "user_role_name": "user",
            "assistant_role_name": "assistant",
            "round_limit": 5,
            "max_tokens": 10000,
            "with_task_specify": False,
            "with_task_planner": False
            }
        }
    params = {
        "session_id": str(uuid.uuid4()),
        "agent_type": "japan",
        "query": "ph值如何调整？",
        "config": json.dumps(config, ensure_ascii=False)  
    }
    if params:
        url = f"{url}?{urlencode(params)}"
    
    print(f"连接URL: {url}")
    
    # 发起请求
    response = requests.get(url, stream=True)
    client = sseclient.SSEClient(response)

    print("已连接到 SSE 流，等待消息...")
    for event in client.events():
        print(f"收到消息: {event.data}")
if __name__ == "__main__":
    # test_agent_config()
    test_stream_qa()