"""
DataAgent 主程序模块。

该脚本用于通过 `agent_orchestrator` 调用 DataAgent，实现基于react调用封装成工具的rag和sql查询功能。程序会在启动时初始化模型与向量集合管理器，
并可通过命令行执行样例查询（例如分析南美白对虾养殖中的 pH 数据）。

"""

import json
from typing import Dict, Any
import agent_orchestrator
from models.model_manager import model_manager
from models.collection_manager import collection_manager
from utils.logger import get_logger
logger = get_logger(__name__)


def run_data_agent(query: str, config: Dict[str, Any] = None) -> str:
    """
    运行 DataAgent，通过 agent_orchestrator 执行查询。

    本函数负责协调 DataAgent 的运行逻辑，包括合并配置、
    启动 agent_orchestrator、支持监听流式结果、并返回最终答案。

    Args:
        query (str): 用户输入的问题或任务描述。例如："分析养殖系统中的 pH 传感器数据"。
        config (Dict[str, Any], optional): 可选的自定义配置字典，用于覆盖默认的 DataAgent 配置。

    Returns:
        str: 来自 DataAgent 的最终回答内容。
             如果执行过程中出现错误，则返回错误信息字符串。

    Raises:
        Exception: 若执行过程中发生未预期的错误，会在日志中记录异常。
    """
    # 默认配置：单dataagent模式(rag参数可选+db参数可选)
    # TODO：flow模式的配置
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

    # 如果外部传入 config，则覆盖默认配置
    if config:
        default_config.update(config)

    logger.info(f"开始运行 DataAgent，查询内容: {query}")
    logger.info(f"当前配置: {json.dumps(default_config, indent=2, ensure_ascii=False)}")

    final_answer = None
    try:
        # 通过 orchestrator 执行主流程
        for result in agent_orchestrator.main(query, default_config):
            if result.get("status") == "final":
                final_answer = result.get("answer", "")
                break
            elif result.get("status") == "error":
                error_msg = f"执行错误: {result.get('reason', '未知错误')}"
                logger.error(error_msg)
                return error_msg

        if not final_answer:
            final_answer = "未从 DataAgent 收到最终回答。"

    except Exception as e:
        error_msg = f"运行过程中发生异常: {str(e)}"
        logger.exception(error_msg)
        return error_msg

    logger.info(f"DataAgent 最终输出: {final_answer}")
    return final_answer


def initialize_managers() -> None:
    """
    初始化全局模型管理器与集合管理器。

    本函数在程序启动时执行，用于加载模型权重、初始化向量存储路径、
    预加载指定集合，以确保 DataAgent 能正常执行语义检索与生成。

    若初始化失败，将记录错误日志并回退至传统模式（不使用预加载集合）。

    Raises:
        Exception: 若初始化任意一个管理器失败，将在日志中记录异常。
    """
    try:
        logger.info("开始初始化全局管理器...")

        # 初始化模型管理器
        if not model_manager.is_initialized():
            model_manager.initialize_models(
                embedding_model_path="models/multilingual-e5-large",
                vector_persist_path="data/vector_data",
                vector_size=1024
            )
            logger.info("模型管理器初始化完成。")

        # 初始化集合管理器
        if not collection_manager.is_initialized():
            collection_manager.initialize_collections(
                persist_path="data/vector_data",
                vector_size=1024,
                preload_collections=["japan_shrimp", "bank"]
            )
            logger.info("集合管理器初始化完成。")

    except Exception as e:
        logger.error(f"全局管理器初始化失败: {e}")
        logger.warning("将使用传统模式继续执行。")


def main() -> int:
    """
    程序主入口函数。

    负责执行以下步骤：
    1. 初始化全局管理器；
    2. 执行示例查询（通过 DataAgent）；
    3. 输出最终结果；
    4. 处理用户中断与异常。

    Returns:
        int: 程序退出状态码。
             - 0 表示正常执行完成；
             - 1 表示被用户中断或出现异常。
    """
    # 初始化
    initialize_managers()

    # 执行查询
    try:
        query = "请检查数据库中的pH传感器数据，并结合知识库中的对虾养殖pH标准来分析"
        config = None
        result = run_data_agent(query, config)

        print("\n" + "=" * 50)
        print("DataAgent 执行结果：")
        print("=" * 50)
        print(result)
        print("=" * 50)
        return 0

    except KeyboardInterrupt:
        print("\n用户中断执行。")
        return 1
    except Exception as e:
        print(f"发生错误: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
