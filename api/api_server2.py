
import os
from flask import Flask, request, jsonify
import logging
import threading
from rag_pipeline.handle_rag.vector_retriever import ModelManager
from prompts.japan_qa import main  as run_japan
from prompts.bank_qa import main as run_bank
import torch
import gc

# --- 初始化 ---
app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("uploadfileAPI")
logger.setLevel(logging.INFO)



def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    
@app.route('/api/upload', methods=['POST'])
def upload_file():
    UPLOAD_FOLDER = 'test/test_data/uploads'
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
        }), 500


# --- 启动服务 ---
if __name__ == '__main__':
    
    # 启动 Flask 应用
    logger.info("Flask服务已启动，正在等待后台智能体初始化完成...")
    app.run(host='0.0.0.0', port=5002)