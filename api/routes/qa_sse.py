import os
import time
import json
from flask import Response, request, jsonify, Blueprint
import logging
from run_qa.orchestrator import main as run_orchestrator
import uuid
from models.model_manager import model_manager
from queue_rag.queue_server import start_rag_service, is_running

logger = logging.getLogger("api_qa_sse")
logger.setLevel(logging.INFO)

sse = Blueprint("sse", __name__, url_prefix="/sse")

# 会话状态：防止客户端自动重连造成重复执行
ACTIVE_SESSIONS = set()
COMPLETED_SESSIONS = set()

def cleanup_old_sessions():
    """定期清理已完成的会话，大于一千条时清理到五百条"""
    global COMPLETED_SESSIONS
    if len(COMPLETED_SESSIONS) > 1000:  # 保留最近1000个
        COMPLETED_SESSIONS = set(list(COMPLETED_SESSIONS)[-500:])  # 清理到500个


@sse.before_app_first_request
def _ensure_global_models_initialized():
    """确保全局 Embedding 模型与向量库在首个请求前初始化。"""
    try:
        if not model_manager.is_initialized():
            logger.info("检测到全局模型未初始化，开始初始化...")
            model_manager.initialize_models(
                embedding_model_path="models/multilingual-e5-large",
                vector_persist_path="data/vector_data",
                vector_size=1024,
                device="auto",
            )
            logger.info("全局模型初始化完成。")
        else:
            logger.info("全局模型已初始化，跳过模型加载。")

        # 确保检索队列服务已启动（用于串行化 Embedding/RAG 检索任务）
        if not is_running():
            logger.info("启动RAG队列服务（FIFO）...")
            #rag队列服务
            start_rag_service(num_workers=1)
            logger.info("RAG队列服务启动完成")
        else:
            logger.info("RAG队列服务已在运行，跳过启动")
    except Exception as e:
        logger.error(f"全局模型初始化失败: {e}")

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
    
    # 清理旧会话
    cleanup_old_sessions()

    # 若会话已完成或正在进行，避免重复执行
    if session_id in COMPLETED_SESSIONS:
        logger.info(f"会话已完成，拒绝请求: {session_id}")
        def empty_gen():
            yield sse_format('{"error": "会话已完成"}')
        return Response(empty_gen(), mimetype="text/event-stream",
                        headers={'Cache-Control': 'no-cache', 'Connection': 'close', 'Access-Control-Allow-Origin': '*'})
    if session_id in ACTIVE_SESSIONS:
        logger.info(f"会话进行中，拒绝重复请求: {session_id}")
        def empty_gen():
            yield sse_format('{"error": "会话已开启}')
        return Response(empty_gen(), mimetype="text/event-stream",
                        headers={'Cache-Control': 'no-cache', 'Connection': 'close', 'Access-Control-Allow-Origin': '*'})
    def generate():
        # 标记会话为活动态
        ACTIVE_SESSIONS.add(session_id)
        final_sent = False
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
            error_data = json.dumps({"error": f"发送初始消息失败: {e}"}, ensure_ascii=False)
            yield sse_format(error_data)
            return
        agent_functions = {
            'japan': run_orchestrator,
            'default': run_orchestrator
        }
        agent_function = agent_functions.get(agent_type, agent_functions['default'])

        # 开始处理消息，仅发送最终答案
        try:    
            config = agent_config

            for i, data in enumerate(agent_function(query, config)):
                if not isinstance(data, dict):
                    continue
                # 处理最终答案
                if data.get("status") == "final":
                    final_message = {
                        "session_id": session_id,
                        "timestamp": time.strftime('%H:%M:%S'),
                        "agent_type": agent_type,
                        "message_id": str(uuid.uuid4()),
                        "content": "查询处理完成，返回最终答案",
                        "data": {
                            "status": "completed",
                            "answer": data.get("answer", "")
                        }
                    }
                    json_data = json.dumps(final_message, ensure_ascii=False)
                    yield sse_format(json_data)
                    logger.info(f"发送最终答案: {json_data}")
                    final_sent = True
                    break
                # 处理错误
                if data.get("status") == "error":
                    error_data = json.dumps({"error": data.get("reason", "unknown error")}, ensure_ascii=False)
                    yield sse_format(error_data)
                    logger.info(f"发送错误: {error_data}")
                    final_sent = True
                    break
        except Exception as e:
            logger.exception("运行失败")
            error_data = json.dumps({"error": f"运行失败: {e}"}, ensure_ascii=False)
            yield sse_format(error_data)
        # 若已发送最终答案，则直接结束连接，不再发送任何消息
        if final_sent:
            COMPLETED_SESSIONS.add(session_id)
            if session_id in ACTIVE_SESSIONS:
                ACTIVE_SESSIONS.remove(session_id)
            return
        
        # 如果没有发送最终答案，发送默认结束消息
        try:
            end_message = {
                "session_id": session_id,
                "timestamp": time.strftime('%H:%M:%S'),
                "agent_type": agent_type,
                "message_id": str(uuid.uuid4()),
                "content": "查询处理结束",
                "data": {
                    "status": "completed",
                    "answer": "处理完成，但未获得有效回答"
                }
            }
            json_data = json.dumps(end_message, ensure_ascii=False)
            yield sse_format(json_data)
            logger.info(f"发送默认结束消息: {json_data}")
        except Exception as e:
            logger.exception("发送结束消息失败")
            error_data = json.dumps({"error": f"发送结束消息失败: {e}"}, ensure_ascii=False)
            yield sse_format(error_data)
        
        # 清理会话状态
        finally:
            COMPLETED_SESSIONS.add(session_id)
            if session_id in ACTIVE_SESSIONS:
                ACTIVE_SESSIONS.remove(session_id)


    return Response(generate(), mimetype="text/event-stream", 
                   headers={
                       'Cache-Control': 'no-cache',
                       'Connection': 'close',
                       'Access-Control-Allow-Origin': '*'
                   })
