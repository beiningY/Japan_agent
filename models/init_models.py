#!/usr/bin/env python3
"""
Embedding模型初始化脚本
可以独立运行来测试embedding模型加载
"""
import logging
import sys
import os
from models.model_manager import model_manager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("EmbeddingModelInitializer")

def main():
    """初始化embedding模型"""
    try:
        logger.info("开始初始化全局Embedding模型管理器...")
        
        # 初始化模型
        device = os.getenv("EMBEDDING_DEVICE", "auto")  # auto, cpu, cuda
        logger.info(f"使用设备: {device}")
        
        model_manager.initialize_models(
            embedding_model_path="models/multilingual-e5-large",
            vector_persist_path="data/vector_data", 
            vector_size=1024,
            device=device
        )
        
        logger.info("Embedding模型初始化完成！")
        
        # 测试模型是否可用
        embedding_model = model_manager.get_embedding_model()
        logger.info(f"Embedding 模型类型: {type(embedding_model)}")
        
        vectorstore = model_manager.get_vectorstore("all_data")
        logger.info(f"向量存储类型: {type(vectorstore)}")
        
        # 测试embedding功能
        test_text = "这是一个测试文本"
        test_embedding = embedding_model.embed_query(test_text)
        logger.info(f"测试embedding维度: {len(test_embedding)}")
        
        logger.info("所有Embedding模型测试通过！")
        return True
        
    except Exception as e:
        logger.error(f"Embedding模型初始化失败: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
