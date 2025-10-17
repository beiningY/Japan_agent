import requests
import json
import uuid
import sseclient
import requests
from urllib.parse import urlencode
import time
from datetime import datetime
import os
def get_query_list():
    query_list = [item['query'] for item in json.load(open('benchmark/南美白对虾问题集.json', 'r'))]
    return query_list

def get_reference_list():
    reference_list = [item['reference'] for item in json.load(open('benchmark/南美白对虾问题集.json', 'r'))]
    return reference_list

def response_agent(query: str):
    url = "http://127.0.0.1:5001/sse/stream_qa"
    config = {
            'rag': {
            'collection_name': 'japan_shrimp',
            'topk_single': 5,
            'topk_multi': 5
            },
            'mode': 'single',
            'single': {
            'temperature': 0.4,
            'system_prompt': '你是数据获取与分析助手。你可以使用 retrieve 工具从知识库检索相关信息，知识库的本文数据更专业属于专业知识供你学习。你也可以同时从数据库中获取实时的相关数据，若查询数据库则需要首先根据需求使用list_sql_tables，get_tables_schema对于数据库的表进行了解，然后再调用执行查询命令的工具read_sql_query。最后根据检索到的真实数据来回答用户的问题。不要直接使用你自己的知识回答，必须基于工具返回的数据。回答中请明确引用来源（文件名/表名），并避免臆断。',
            'max_tokens': 10000,
            }
        }
    params = {
        "session_id": str(uuid.uuid4()),
        "agent_type": "japan",
        "query": query,
        "config": json.dumps(config, ensure_ascii=False)  
    }
    if params:
        url = f"{url}?{urlencode(params)}"
    
    print(f"连接URL: {url}")
    
    response_content = ""
    try:
        # 发起请求
        response = requests.get(url, stream=True)
        client = sseclient.SSEClient(response)

        print("已连接到 SSE 流，等待消息...")
        message_count = 0
        for event in client.events():
            message_count += 1
            print(f"收到消息 {message_count}: {event.data}")
            
            # 解析消息检查是否完成
            try:
                data = json.loads(event.data)
                
                # 收集响应内容
                if data.get("data", {}).get("answer"):
                    response_content += data["data"]["answer"]
                
                if data.get("data", {}).get("status") == "completed":
                    print("收到完成消息，主动断开连接")
                    break
                if "error" in data:
                    print("收到错误消息，断开连接")
                    response_content = f"错误: {data.get('error', '未知错误')}"
                    break
            except json.JSONDecodeError:
                pass
        
                
    except requests.exceptions.ConnectionError as e:
        print(f"连接失败: {e}")
        print("请确保服务器正在运行在 localhost:5001")
        response_content = f"连接失败: {e}"
    except Exception as e:
        print(f"SSE连接出错: {e}")
        response_content = f"SSE连接出错: {e}"
    finally:
        print("SSE连接已结束")
    
    return response_content

def eval_agent(query: str):
    response = response_agent(query)
    return response

if __name__ == "__main__":

    query_list = get_query_list()
    reference_list = get_reference_list()
    
    # 收集所有结果
    results = []
    total_time = 0
    
    for idx, (query, reference) in enumerate(zip(query_list, reference_list), 1):
        start_time = time.time()
        response = eval_agent(query)
        end_time = time.time()  
        elapsed_time = end_time - start_time
        total_time += elapsed_time
        
        print("-"*100)
        print(f"查询: {query}")
        print(f"回答: {response}")
        print(f"查询时间: {elapsed_time:.2f}秒")
        print(f"参考答案: {reference}")
        print("-"*100)
        
        # 添加到结果列表
        results.append({
            "id": idx,
            "query": query,
            "response": response,
            "reference": reference,
            "latency": round(elapsed_time, 2)
        })
    
    avg_time = total_time / len(query_list) if query_list else 0
    print(f"平均查询时间: {avg_time:.2f}秒")
    
    # 保存结果到JSON文件
    results_dir = "benchmark/results"
    os.makedirs(results_dir, exist_ok=True)

    output_file = os.path.join(results_dir, f"qa_eval.json")
    
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "total_queries": len(query_list),
        "average_time": round(avg_time, 2),
        "results": results
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存到: {output_file}")