# /usr/sarah/Camel_agent/api_server.py

from flask import Flask, request, jsonify
import logging
import threading
from dataprocess.get_unadded_data import get_unadded_log_list  
from main import main  as run 
from agents import ChatMultiAgent
# --- 初始化 ---
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CamelAgentAPI")

chat_agent = None
is_ready = False # <-- 新增一个状态标志

def initialize_agent():
    """在后台线程中执行耗时的初始化。"""
    global chat_agent, is_ready
    logger.info("后台初始化线程已启动...")
    try:
        agent_instance = ChatMultiAgent()
        # --- [关键] 预热调用 ---
        # 尝试用一个无意义的、简单的输入来调用一次run方法，以触发所有模型的加载。
        logger.info("正在预热 ChatMultiAgent，这可能需要几分钟...")
        # agent_instance.run("预热查询，请忽略。")
        
        chat_agent = agent_instance
        is_ready = True
        logger.info("ChatMultiAgent 已预热完毕，服务准备就绪！")
    except Exception as e:
        logger.error(f"后台初始化 ChatMultiAgent 失败: {e}", exc_info=True)


# --- API 端点 ---
@app.route('/api/run_query', methods=['POST'])
def run_query():
    if not is_ready or not chat_agent:
        return jsonify({"error": "专家智能体正在初始化中，请稍后再试。"}), 503 


    data = request.json
    if not data or 'query' not in data:
        return jsonify({"error": "请求体中必须包含 'query' 字段。"}), 400

    query = data['query']
    print(f"收到查询请求: '{query}'")
    logger.info(f"收到查询请求: '{query}'")

    try:
        # 调用 run 方法
        output_msg = run(query)
        # 根据您上次的提示，我们假设结果是一个对象或字典
        if hasattr(output_msg, 'content'):
            response_content = output_msg.content
        elif isinstance(output_msg, dict) and 'content' in output_msg:
            response_content = output_msg['content']
        else:
            response_content = str(output_msg)

        logger.info("查询成功完成。")
        return jsonify({"result": response_content})

    except Exception as e:
        logger.exception(f"执行 chat_agent.run 时出错: {e}")
        return jsonify({"error": f"执行查询时发生内部错误: {str(e)}"}), 500



@app.route('/api/get_log_list', methods=['POST'])
def unadded_log_list():
    list = request.json
    if not list :
        return jsonify({"error": "请求未知错误"}), 400
    logger.info(f"收到获取未添加日志请求")
    try:
        unadded_log_list = get_unadded_log_list()
        logger.info("查询成功完成。")
        return jsonify({"result": unadded_log_list})

    except Exception as e:
        logger.exception(f"执行请求未添加日志时出错: {e}")
        return jsonify({"error": f"执行请求未添加日志时发生内部错误: {str(e)}"}), 500



# --- 启动服务 ---
if __name__ == '__main__':
    # 启动后台初始化线程
    init_thread = threading.Thread(target=initialize_agent)
    init_thread.daemon = True 
    init_thread.start()
    
    # 启动 Flask 应用
    logger.info("Flask服务已启动，正在等待后台智能体初始化完成...")
    app.run(host='0.0.0.0', port=5001)