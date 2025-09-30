#!/usr/bin/env python3
"""
Main function to run DataAgent through agent_orchestrator with command line arguments.
"""
from utils.logger import get_logger
logger = get_logger(__name__)
import json
from typing import Dict, Any
import agent_orchestrator
from models.model_manager import model_manager
from models.collection_manager import collection_manager


def run_data_agent(query: str, config: Dict[str, Any] = None) -> str:
    """
    Run DataAgent through agent_orchestrator.

    Args:
        query: User query to process
        config: Optional configuration for orchestration

    Returns:
        Final answer from the agent by SSE
    """
    # Set default config to use single mode for DataAgent
    default_config = {
        "mode": "single",
        "rag": {
            "collection_name": "japan_shrimp",
            "topk_single": 5,
        },
        "single": {
            "temperature": 0.4,
            "max_tokens": 4096
        }
    }

    # Merge with provided config
    if config:
        default_config.update(config)

    logger.info(f"Running DataAgent with query: {query}")
    logger.info(f"Config: {json.dumps(default_config, indent=2, ensure_ascii=False)}")

    # Run orchestrator and collect results
    final_answer = None
    try:
        for result in agent_orchestrator.main(query, default_config):
            if result.get("status") == "final":
                final_answer = result.get("answer", "")
                break
            elif result.get("status") == "error":
                error_msg = f"Error: {result.get('reason', 'Unknown error')}"
                logger.error(error_msg)
                return error_msg

        if not final_answer:
            final_answer = "No final answer received from agent."

    except Exception as e:
        error_msg = f"Exception occurred: {str(e)}"
        logger.exception(error_msg)
        return error_msg

    logger.info(f"Final answer: {final_answer}")
    return final_answer


def initialize_managers():
    """初始化全局管理器"""
    try:
        logger.info("开始初始化全局管理器...")
        
        # 初始化模型管理器
        if not model_manager.is_initialized():
            model_manager.initialize_models(
                embedding_model_path="models/multilingual-e5-large",
                vector_persist_path="data/vector_data",
                vector_size=1024
            )
            logger.info("全局模型管理器初始化完成")
        
        # 初始化集合管理器
        if not collection_manager.is_initialized():
            collection_manager.initialize_collections(
                persist_path="data/vector_data",
                vector_size=1024,
                preload_collections=["japan_shrimp", "bank", "all_data", "knowledge_base"]
            )
            logger.info("全局集合管理器初始化完成")
            
    except Exception as e:
        logger.error(f"全局管理器初始化失败: {e}")
        logger.warning("将使用传统模式")


def main():
    """Main function with command line argument parsing."""
    
    # 初始化全局管理器
    initialize_managers()

    # Run the agent
    try:
        query = "请检查数据库中的pH传感器数据，并结合知识库中的对虾养殖pH标准来分析"
        config = None
        result = run_data_agent(query, config)
        print("\n" + "="*50)
        print("DataAgent Result:")
        print("="*50)
        print(result)
        print("="*50)
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())