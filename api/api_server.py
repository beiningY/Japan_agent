
import os
from flask import Flask, request, jsonify
import logging
import threading
from rag.camel_rag import ModelManager
from agents.multi_agent import main  as run_japan
from run_qa.bank_qa import main as run_bank
from run_qa.orchestrator import main as run_orchestrator
import torch
import gc

# --- 初始化 ---
app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AgentHttpAPI")
logger.setLevel(logging.INFO)



loaded_model = False
loaded_tokenizer = False

def initialize_agent():
    global loaded_model
    logger.info("后台初始化线程已启动...")
    try:
        # 模型预热（embedding）
        manager = ModelManager()
        manager.get_embedding_model()
        loaded_model = True
        logger.info("服务准备就绪！")
    except Exception as e:
        logger.error(f"embedding模型初始化失败: {e}", exc_info=True)

def initialize_tokenizer():
    global loaded_tokenizer
    logger.info("后台初始化线程已启动...")
    try:
        manager = ModelManager()
        manager.get_tokenizer()
        loaded_tokenizer = True
    except Exception as e:
        logger.error(f"tokenizer初始化失败: {e}", exc_info=True)


@app.route('/api/run_query', methods=['POST'])
def run_query():

    if not request.is_json:
        return jsonify({"error": "必须为 JSON 格式"}), 400

    data = request.json
    if 'query' not in data:
        return jsonify({"error": "缺少 'query' 字段"}), 400

    query = data['query'].strip()
    if not query:
        return jsonify({"error": "查询内容不能为空"}), 400

    logger.info(f"收到查询: {query}")
    agent_type = data['agent_type']
    if not agent_type:
        return jsonify({"error": "智能体类型不能为空"}), 400
    if agent_type == 'japan':
        try:
            response = run_japan(query)
            content = getattr(response, 'content', str(response))
            return jsonify({"result": content})
        except Exception as e:
            logger.exception("运行失败")
            return jsonify({"error": "服务器内部错误"}), 500


    elif agent_type == 'bank':
        try:
            response = run_bank(query)
            content = getattr(response, 'content', str(response))
            return jsonify({"result": content})
        except Exception as e:
            logger.exception("运行失败")
            return jsonify({"error": "服务器内部错误"}), 500

    elif agent_type == 'orchestrator':
        try:
            config = data.get('config') or {}
            # orchestrator returns a generator; stream internally and return last agent_response
            gen = run_orchestrator(query, config)
            last_response = None
            for chunk in gen:
                if isinstance(chunk, dict) and 'agent_response' in chunk:
                    last_response = chunk['agent_response']
            return jsonify({"result": last_response or ""})
        except Exception as e:
            logger.exception("运行失败")
            return jsonify({"error": "服务器内部错误"}), 500


    
"""@app.route('/api/upload', methods=['POST'])
def upload_file():
    UPLOAD_FOLDER = 'data/raw_data/uploads'
    ALLOWED_EXTENSIONS = {'txt', 'pdf'}
    # 检查文件是否存在
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "未找到文件字段"}), 400
    file = request.files['file']
    # 检查文件名
    if file.filename == '':
        return jsonify({"status": "error", "message": "未选择文件"}), 400
    
    # 验证文件类型
    if not (file and allowed_file(file.filename)):
        return jsonify({
            "status": "error",
            "message": f"不支持的文件类型，允许: {', '.join(ALLOWED_EXTENSIONS)}"
        }), 400
    
    try:
        # 保存文件
        file.save(os.path.join(UPLOAD_FOLDER, file.filename))
        
        # 返回成功响应
        return jsonify({
            "status": "success",
            "filename": file.filename,
            "url": f"/uploads/{file.filename}"
        }), 200
        
    except Exception as e:
        app.logger.error(f"文件上传失败: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "服务器处理文件失败"
        }), 500"""

# 预定义知识库配置
KB_CONFIG = {
    "cede3e0b-6447-4418-9c80-97129710beb5": {
        "name": "银行相关",
        "path": "data/raw_data/bank"
    },
    "25241d69-33fd-465d-8fd1-18d34865248c": {
        "name": "陆上养殖",
        "path": "data/raw_data/japan_shrimp"
    }
}

@app.route("/api/get_knowledge_base_list", methods=["GET"])
def get_kb_list():
    # 从查询参数获取 kb_ids（格式：?kb_ids=id1,id2,id3）
    kb_ids_str = request.args.get("kb_ids", "")
    if not kb_ids_str:
        return jsonify({"error": "缺少 kb_ids 参数"}), 400
    
    kb_ids = kb_ids_str.split(",")
    result = []
    
    for kb_id in kb_ids:
        if kb_id not in KB_CONFIG:
            return jsonify({"error": f"无效的 kb_id: {kb_id}"}), 404
            logger.info("运行失败")
        kb_path = KB_CONFIG[kb_id]["path"]
        if not os.path.isdir(kb_path):
            return jsonify({"error": f"知识库路径不存在: {kb_path}"}), 404
            logger.info("运行失败")
        try:
            files = [
                f for f in os.listdir(kb_path) 
                if not f.startswith('.') and not f.startswith('__')
            ]
            
            result.append({
                "kb_id": kb_id,
                "kb_name": KB_CONFIG[kb_id]["name"],
                "files": files
            })
        except Exception as e:
            return jsonify({"error": f"读取文件列表失败: {str(e)}"}), 500
            logger.info("运行失败")
    logger.info("返回列表")
    return jsonify({"status": "success", "data": result})

# --- 启动服务 ---
if __name__ == '__main__':
    # 启动后台初始化线程
    init_thread = threading.Thread()
    init_thread.daemon = True 
    init_thread.start()
    
    # 启动 Flask 应用
    logger.info("Flask服务已启动，正在等待后台智能体初始化完成...")
    app.run(host='0.0.0.0', port=5001)