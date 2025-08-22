from flask import Flask, request, jsonify
from api.routes.knowledge_base import knowledgebase
from api.routes.qa_sse import sse
import logging
import threading
import os

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

# --- 启动服务 ---
if __name__ == '__main__':
    # 启动后台初始化线程
    init_thread = threading.Thread()
    init_thread.daemon = True 
    init_thread.start()
    
    # 启动 Flask 应用
    logger.info("Flask服务已启动，正在等待后台智能体初始化完成...")
    app.run(host='0.0.0.0', port=5001, debug=True)
