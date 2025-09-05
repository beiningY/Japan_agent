import os
import time
import json
from flask import Flask, Response, request, jsonify, Blueprint
import logging
from agents.langchain_single_agent import LangchainSingleAgent
from run_qa.orchestrator import main as run_orchestrator
import uuid

logger = logging.getLogger("api_qa_sse")
logger.setLevel(logging.INFO)

sse = Blueprint("sse", __name__, url_prefix="/sse")


@sse.route('/agent_config', methods=['GET'])
def agent_config():
    logger.info("收到请求,返回agent_config")
    config = json.load(open("config/config_description.json", "r", encoding="utf-8"))
    return jsonify(config)



def sse_format(data: str):
    """格式化成 SSE 数据格式"""
    return f"data: {data}\n\n"

@sse.route('/stream_qa', methods=['GET', 'POST'])
def stream():
    try:
        if request.method == 'GET':
            logger.info(f"收到SSE请求{request}")
            session_id = request.args.get('session_id', str(uuid.uuid4()))
            query = request.args.get('query', '请介绍日本陆上养殖项目')
            agent_type = request.args.get('agent_type', 'japan')
            agent_config = json.loads(request.args.get('config', None))

        else:  # POST
            logger.info(f"收到SSE请求{request.get_json()}")
            data = request.get_json() or {}
            session_id = data.get('session_id', str(uuid.uuid4()))
            query = data.get('query', '请介绍日本陆上养殖项目')
            agent_type = data.get('agent_type', 'japan')
            agent_config = json.loads(data.get('config', None))
    except Exception as e:
        logger.error(f"收到SSE请求失败{e}")
        return jsonify({"error": "收到SSE请求失败"}), 400
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
            logger.info(f"发送初始消息: {json_data}")
        except Exception as e:
            logger.exception("发送初始消息失败")
            error_data = json.dumps({"error": "发送初始消息失败"}, ensure_ascii=False)
            yield sse_format(error_data)
            return
        agent_functions = {
            'japan': run_orchestrator,
            #'bank': LangchainSingleAgent().run,
            'default': run_orchestrator
        }
        agent_function = agent_functions.get(agent_type, agent_functions['default'])

        # 开始处理消息并发送数据
        try:    
            config = agent_config
        
            for i, data in enumerate(agent_function(query, config)):
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
                    logger.info(f"发送消息: {json_data}")
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
            logger.info(f"发送结束消息: {json_data}")
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
