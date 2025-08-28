from flask import Flask, request, jsonify
from api.routes.knowledge_base import knowledgebase
from api.routes.qa_sse import sse
import logging
import threading
import os
from models.model_manager import model_manager

app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("API_Server")
logger.setLevel(logging.INFO)

# 注册路由
app.register_blueprint(knowledgebase)
app.register_blueprint(sse)

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

def initialize_models():
    """初始化全局Embedding模型管理器"""
    try:
        logger.info("开始初始化全局Embedding模型管理器...")
        model_manager.initialize_models(
            embedding_model_path="models/multilingual-e5-large",
            vector_persist_path="data/vector_data",
            vector_size=1024
        )
        logger.info("全局Embedding模型管理器初始化完成！")
    except Exception as e:
        logger.error(f"Embedding模型初始化失败: {e}")
        # 可以选择继续运行（降级到传统模式）或退出
        logger.warning("将使用传统模式（每次调用时加载embedding模型）")

# --- 启动服务 ---
if __name__ == '__main__':
    # 检查是否是Flask的重启进程
    import os
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        # 只在主进程中初始化模型，避免debug重启时重复初始化
        logger.info("主进程启动，初始化Embedding模型...")
        initialize_models()
    else:
        # 这是Flask重启后的子进程，不需要重新初始化
        logger.info("Flask重启进程，跳过模型初始化")
    
    # 启动 Flask 应用
    logger.info("启动Flask服务...")
    app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)
