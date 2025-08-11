import time
import json
from flask import Flask, Response, request, jsonify
import logging
from prompts.japan_qa import main  as run_japan
from prompts.bank_qa import main as run_bank
import uuid
app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AgentSseAPI")
logger.setLevel(logging.INFO)

def sse_format(data: str):
    """格式化成 SSE 数据格式"""
    return f"data: {data}\n\n"

@app.route('/stream', methods=['GET', 'POST'])
def stream():
    # 获取参数（支持GET和POST）
    if request.method == 'GET':
        session_id = request.args.get('session_id', str(uuid.uuid4()))
        query = request.args.get('query', '请介绍日本陆上养殖项目')
        agent_type = request.args.get('agent_type', 'japan')
    else:  # POST
        data = request.get_json() or {}
        session_id = data.get('session_id', uuid.uuid4())
        query = data.get('query', '请介绍日本陆上养殖项目')
        agent_type = data.get('agent_type', 'japan')
    
    # 记录接收到的参数
    logger.info(f"收到SSE请求 - Session ID: {session_id}, Query: {query}, Agent Type: {agent_type}")
    def generate():
        try:
            # 发送开始消息
            start_message = {
                "session_id": session_id,
                "timestamp": time.strftime('%H:%M:%S'),
                "agent_type": agent_type,
                "message_id": str(uuid.uuid4()),
                "content": f"开始处理查询: '{query}'",
                "data": {
                    "status": "started"
                }
            }
            json_data = json.dumps(start_message, ensure_ascii=False)
            yield sse_format(json_data)
        except Exception as e:
            logger.exception("发送初始消息失败")
            error_data = json.dumps({"error": "发送初始消息失败"}, ensure_ascii=False)
            yield sse_format(error_data)
            return
        agent_functions = {
            'japan': run_japan,
            'bank': run_bank,
            'default': run_japan
        }
        agent_function = agent_functions.get(agent_type, agent_functions['default'])

        # 开始处理消息并发送数据
        try:    
            for i, data in enumerate(agent_function(query)):
                if data:
                    message = {
                        "session_id": session_id,
                        "timestamp": time.strftime('%H:%M:%S'),
                        "agent_type": agent_type,
                        "message_id": str(uuid.uuid4()),
                        "content": f"查询中，智能体正在执行第{i+1}步",
                        "data": {
                            "status": "processing",
                            "step": i+1,
                            "response": data
                        }
                    }
                    json_data = json.dumps(message, ensure_ascii=False)
                    yield sse_format(json_data)
        except Exception as e:
            logger.exception("运行失败")
            error_data = json.dumps({"error": "服务器内部错误"}, ensure_ascii=False)
            yield sse_format(error_data)
        # 发送结束消息
        try:
            end_message = {
                "session_id": session_id,
                "timestamp": time.strftime('%H:%M:%S'),
                "agent_type": agent_type,
                "message_id": str(uuid.uuid4()),
                "content": "查询处理结束",
                "data": {
                        "status": "completed",
                }
            }
            json_data = json.dumps(end_message, ensure_ascii=False)
            yield sse_format(json_data)
        except Exception as e:
            logger.exception("发送结束消息失败")
            error_data = json.dumps({"error": "发送结束消息失败"}, ensure_ascii=False)
            yield sse_format(error_data)


    return Response(generate(), mimetype="text/event-stream", 
                   headers={
                       'Cache-Control': 'no-cache',
                       'Connection': 'keep-alive',
                       'Access-Control-Allow-Origin': '*'
                   })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True, threaded=True)
