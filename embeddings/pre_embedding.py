#!/usr/bin/env python3
"""
批量向量化脚本 - 使用CAMEL RAG框架手动处理结构化数据

用途：
    - 批量处理JSON格式的结构化数据
    - 使用自定义chunking策略（按标题或日志格式）
    - 初始化知识库向量数据

使用方法：
    1. 直接运行（处理默认配置的数据）：
       python pre_embedding.py
    
    2. 命令行指定参数：
       python pre_embedding.py --collection japan_shrimp --file data/json_data/book.json
    
    3. 在代码中导入使用：
       from embeddings.pre_embedding import batch_embed
       batch_embed("my_collection", "data/my_data.json", chunk_type="title")
"""

import sys
import os
import argparse
import logging

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from embeddings.japan_book_chunking import chunk_data_for_log, chunk_data_by_title
from rag.camel_rag import CamelRAG

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("BatchEmbedding")


# ==================== 配置区域 ====================
# 可以在这里修改默认配置

DEFAULT_CONFIGS = {
    "japan_shrimp": {
        "collection_name": "japan_shrimp",
        "files": [
            {
                "path": "data/json_data/data_json_book_zh.json",
                "chunk_type": "title",
                "max_tokens": 500,
                "enabled": False  # 设为True启用
            },
            {
                "path": "data/json_data/data_json_feed.json",
                "chunk_type": "title",
                "max_tokens": 500,
                "enabled": True
            },
            {
                "path": "data/json_data/data_json_log.json",
                "chunk_type": "log",
                "max_tokens": 500,
                "enabled": True
            }
        ]
    },
    # 可以添加更多配置
    # "bank": {
    #     "collection_name": "bank",
    #     "files": [...]
    # }
}

# ==================== 函数定义 ====================

def get_chunk_function(chunk_type: str):
    """根据类型名称获取chunking函数
    
    Args:
        chunk_type: "title" 或 "log"
    
    Returns:
        对应的chunking函数
    """
    if chunk_type == "title":
        return chunk_data_by_title
    elif chunk_type == "log":
        return chunk_data_for_log
    else:
        raise ValueError(f"不支持的chunk类型: {chunk_type}，支持的类型: title, log")


def batch_embed(
    collection_name: str,
    data_path: str,
    chunk_type: str = "title",
    max_tokens: int = 500
):
    """批量向量化单个文件
    
    Args:
        collection_name: 知识库集合名称
        data_path: JSON数据文件路径
        chunk_type: chunking类型 ("title" 或 "log")
        max_tokens: 每个chunk的最大token数
    """
    logger.info("=" * 60)
    logger.info(f"开始处理: {data_path}")
    logger.info(f"目标集合: {collection_name}")
    logger.info(f"Chunk类型: {chunk_type}, Max tokens: {max_tokens}")
    logger.info("=" * 60)
    
    try:
        # 检查文件是否存在
        if not os.path.exists(data_path):
            logger.error(f"❌ 文件不存在: {data_path}")
            return False
        
        # 初始化CamelRAG
        rag = CamelRAG(collection_name=collection_name)
        
        # 获取chunking函数
        chunk_func = get_chunk_function(chunk_type)
        
        # 执行向量化
        rag.embedding(
            data_path=data_path,
            chunk_type=chunk_func,
            max_tokens=max_tokens
        )
        
        # 释放资源
        rag.release()
        
        logger.info("=" * 60)
        logger.info(f"✅ 成功完成: {data_path}")
        logger.info("=" * 60)
        logger.info("")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 处理失败: {data_path}")
        logger.error(f"   错误信息: {e}")
        return False


def batch_embed_config(config_name: str):
    """根据配置名称批量处理多个文件
    
    Args:
        config_name: 配置名称（如"japan_shrimp"）
    """
    if config_name not in DEFAULT_CONFIGS:
        logger.error(f"❌ 配置不存在: {config_name}")
        logger.info(f"   可用配置: {list(DEFAULT_CONFIGS.keys())}")
        return False
    
    config = DEFAULT_CONFIGS[config_name]
    collection_name = config["collection_name"]
    
    logger.info("🚀 开始批量向量化")
    logger.info(f"   配置: {config_name}")
    logger.info(f"   集合: {collection_name}")
    logger.info("")
    
    success_count = 0
    fail_count = 0
    
    for file_config in config["files"]:
        if not file_config.get("enabled", True):
            logger.info(f"⏭️  跳过（已禁用）: {file_config['path']}")
            continue
        
        result = batch_embed(
            collection_name=collection_name,
            data_path=file_config["path"],
            chunk_type=file_config["chunk_type"],
            max_tokens=file_config["max_tokens"]
        )
        
        if result:
            success_count += 1
        else:
            fail_count += 1
    
    logger.info("=" * 60)
    logger.info("📊 批量处理完成")
    logger.info(f"   成功: {success_count} 个文件")
    logger.info(f"   失败: {fail_count} 个文件")
    logger.info("=" * 60)
    
    return fail_count == 0


# ==================== 主程序 ====================

def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(
        description="批量向量化工具 - 处理结构化JSON数据"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        help=f"使用预定义配置 ({', '.join(DEFAULT_CONFIGS.keys())})"
    )
    
    parser.add_argument(
        "--collection",
        type=str,
        help="知识库集合名称"
    )
    
    parser.add_argument(
        "--file",
        type=str,
        help="JSON数据文件路径"
    )
    
    parser.add_argument(
        "--chunk-type",
        type=str,
        choices=["title", "log"],
        default="title",
        help="Chunking类型 (默认: title)"
    )
    
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=500,
        help="每个chunk的最大token数 (默认: 500)"
    )
    
    args = parser.parse_args()
    
    # 模式1: 使用预定义配置
    if args.config:
        success = batch_embed_config(args.config)
        sys.exit(0 if success else 1)
    
    # 模式2: 指定单个文件
    elif args.collection and args.file:
        success = batch_embed(
            collection_name=args.collection,
            data_path=args.file,
            chunk_type=args.chunk_type,
            max_tokens=args.max_tokens
        )
        sys.exit(0 if success else 1)
    
    # 模式3: 无参数，使用默认配置
    else:
        logger.info("未指定参数，使用默认配置: japan_shrimp")
        logger.info("可用参数：")
        logger.info("  --config japan_shrimp           使用预定义配置")
        logger.info("  --collection NAME --file PATH   处理单个文件")
        logger.info("")
        
        success = batch_embed_config("japan_shrimp")
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
