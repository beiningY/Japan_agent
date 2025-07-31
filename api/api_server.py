
import os
from flask import Flask, request, jsonify
import logging
import threading
from rag_pipeline.handle_rag.vector_retriever import ModelManager
from prompts.japan_qa import main  as run 
# --- 初始化 ---
app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AgentAPI")
logger.setLevel(logging.INFO)
 
UPLOAD_FOLDER = 'data/raw_data/uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf'}
# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# 全局预热（只执行一次）
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

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/run_query', methods=['POST'])
def run_query():
    if not loaded_model:
        return jsonify({"error": "服务初始化中，请稍后..."}), 503

    if not request.is_json:
        return jsonify({"error": "必须为 JSON 格式"}), 400

    data = request.json
    if 'query' not in data:
        return jsonify({"error": "缺少 'query' 字段"}), 400

    query = data['query'].strip()
    if not query:
        return jsonify({"error": "查询内容不能为空"}), 400

    logger.info(f"收到查询: {query}")
    try:
        response = run(query)
        content = getattr(response, 'content', str(response))
        return jsonify({"result": content})
    except Exception as e:
        logger.exception("运行失败")
        return jsonify({"error": "服务器内部错误"}), 500
    
@app.route('/api/upload', methods=['POST'])
def upload_file():
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
        }), 500
# --- 启动服务 ---
if __name__ == '__main__':
    # 启动后台初始化线程
    init_thread = threading.Thread(target=initialize_agent)
    init_thread.daemon = True 
    init_thread.start()
    
    # 启动 Flask 应用
    logger.info("Flask服务已启动，正在等待后台智能体初始化完成...")
    app.run(host='0.0.0.0', port=5001)