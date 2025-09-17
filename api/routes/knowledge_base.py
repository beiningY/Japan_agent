from flask import Blueprint, jsonify, request
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("api_knowledgebase")
logger.setLevel(logging.INFO)
from ToolOrchestrator.tools.kb_tools import create, delete, add_file, deletefile

knowledgebase = Blueprint("knowledge_base", __name__, url_prefix="/knowledge_base")


@knowledgebase.route('/upload_file', methods=['POST'])
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
        }), 500

@knowledgebase.route('/create_kb', methods=['GET'])
def create_kb():
    kb_name = request.args.get('kb_name')
    try:
        create(kb_name)
        return jsonify({"status": "success", "message": "知识库创建成功"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@knowledgebase.route('/delete_kb', methods=['GET'])
def delete_kb():
    kb_name = request.args.get('kb_name')
    try:
        delete(kb_name)
        return jsonify({"status": "success", "message": "知识库删除成功"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@knowledgebase.route('/embedding_file', methods=['GET'])
def embedding_file():
    # 需要对应知识库类别名称和文件路径
    kb_name = request.args.get('kb_name')
    file_name = request.args.get('file_name')
    try:
        add_file(file_name, kb_name)
        return jsonify({"status": "success", "message": "文件向量化成功"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@knowledgebase.route('/delete_file', methods=['GET'])
def delete_file():
    kb_name = request.args.get('kb_name')
    file_name = request.args.get('file_name')
    try:
        deletefile(file_name, kb_name)
        return jsonify({"status": "success", "message": "文件删除成功"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
