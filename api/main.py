from flask import Flask, request, jsonify
from api.routes.knowledge_base import knowledgebase
from api.routes.qa_sse import sse
import logging
import threading
import os
import asyncio
from models.model_manager import model_manager
from models.collection_manager import collection_manager
from queue_rag.queue_server import start_rag_service, is_running
from utils.global_tool_manager import async_initialize_global_tools

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


def initialize_models():
    """初始化全局Embedding模型管理器和集合管理器"""
    # 初始化Embedding模型
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

    # 初始化全局集合管理器
    try:
        logger.info("开始初始化全局集合管理器...")
        collection_manager.initialize_collections(
            persist_path="data/vector_data",
            vector_size=1024,
            preload_collections=["japan_shrimp", "bank", "all_data", "knowledge_base"]
        )
        logger.info("全局集合管理器初始化完成！")
    except Exception as e:
        logger.error(f"集合管理器初始化失败: {e}")
        logger.warning("将使用传统模式（每次调用时创建集合连接）")

    # 初始化全局MCP工具注册器
    try:
        logger.info("开始初始化全局MCP工具注册器...")
        
        # 在当前线程中创建新的事件循环来运行异步初始化
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            success = loop.run_until_complete(async_initialize_global_tools())
            if success:
                logger.info("全局MCP工具注册器初始化完成！")
            else:
                logger.error("全局MCP工具注册器初始化失败")
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"MCP工具注册器初始化失败: {e}")
        logger.warning("将继续运行，但MCP工具功能可能不可用")

    # 启动队列服务
    try:
        if not is_running():
            logger.info("启动RAG队列服务（单线程，FIFO）...")
            start_rag_service(num_workers=1)
            logger.info("RAG队列服务启动完成")
        else:
            logger.info("RAG队列服务已在运行，跳过启动")
    except Exception as e:
        logger.error(f"RAG队列服务启动失败: {e}")

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
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)
