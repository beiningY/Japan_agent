import sseclient
import requests
from urllib.parse import urlencode

def connect_sse(url, session_id=None, query=None, agent_type=None):
    """连接SSE服务器并传递参数
    
    Args:
        url (str): SSE服务器地址
        session_id (str, optional): 会话ID
        query (str, optional): 查询内容
        agent_type (str, optional): 代理类型
    """
    # 构建查询参数字典
    params = {}
    if session_id:
        params['session_id'] = session_id
    if query:
        params['query'] = query
    if agent_type:
        params['agent_type'] = agent_type
    
    # 如果有参数，添加到URL中
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
    # 示例调用 - 传递所有参数
    
    connect_sse(
        "http://localhost:5001/stream",
        session_id="session_123",
        query="如何调整ph值",
        agent_type="japan"
    )
    
    # 也可以只传递部分参数
    # connect_sse(
    #    "http://localhost:5001/stream",
    #    session_id="session_456",
    #    query="贷款有哪些类型？"
    #)
    
    # 或者不传递任何参数（保持原有行为）
    # connect_sse("http://localhost:5001/stream")