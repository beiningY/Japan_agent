from flask import Blueprint, jsonify, request
import os
import logging
logger = logging.getLogger("api_knowledgebase")
logger.setLevel(logging.INFO)

knowledgebase = Blueprint("knowledge_base", __name__, url_prefix="/knowledge_base")

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
@knowledgebase.route("/get_list", methods=["GET"])
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

