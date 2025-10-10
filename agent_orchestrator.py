from __future__ import annotations
import asyncio
from typing import Any, Dict, Generator, Optional
from pydantic import BaseModel, Field
from agents import DataAgent
from utils.logger import get_logger
logger = get_logger(__name__)

class RAGConfig(BaseModel):
    """
    RAGConfig 配置类，用于配置 RAG 相关参数
    """
    collection_name: Optional[str] = "japan_shrimp"
    topk_single: Optional[int] = 5


class SingleTurnConfig(BaseModel):
    """
    对于single agent进行配置和选择
    """
    system_prompt: Optional[str] = "你是数据获取与分析助手。请使用工具获取知识库与数据库的真实数据；然后根据真实的数据来回答用户的问题。回答中请明确引用来源（表名/文件名），并避免臆断。"
    temperature: Optional[float] = 0.4
    max_tokens: Optional[int] = 4096


class OrchestrationConfig(BaseModel):
    """
    对于传入的参数进行配置解析
    """

    mode: str = "auto"
    rag: RAGConfig = Field(default_factory=RAGConfig)
    single: SingleTurnConfig = Field(default_factory=SingleTurnConfig)



import asyncio
from typing import Dict, Any, Generator
from utils.logger import get_logger

logger = get_logger(__name__)

def _run_single(query: str, cfg) -> Generator[Dict[str, Any], None, str]:
    """
    执行 DataAgent 并逐步记录所有输出内容。
    不进行任何逻辑判断或提前终止，所有 step() 的输出都被记录与 yield。
    """
    from agents.data_agent import DataAgent  # 按需修改为你项目中的导入路径

    logger.info("=== 启动 DataAgent 单轮运行 ===")
    logger.info(f"用户输入: {query}")

    # 初始化 Agent
    agent = DataAgent(system_prompt=cfg.single.system_prompt)
    agent.update_memory("user", query)

    max_steps = getattr(cfg.single, "max_steps", 4)

    for step_index in range(1, max_steps + 1):
        logger.info(f"\n------ Step {step_index} 开始 ------")
        try:
            # 执行一步
            result = asyncio.run(agent.step())

            # 打印和记录
            logger.info(f"[Step {step_index} 输出]\n{result}\n")

            yield {
                "step": step_index,
                "output": result
            }

        except Exception as e:
            logger.exception(f"[Step {step_index}] 执行异常: {e}")
            yield {
                "step": step_index,
                "status": "error",
                "reason": str(e)
            }
            break

    logger.info("=== DataAgent 单轮运行结束 ===")
    yield {"status": "done"}
    return "completed"

def _debug_run_single(query: str, cfg) -> Generator[Dict[str, Any], None, str]:
    """
    调试版：打印模型每一步 step() 的完整输出，不做任何过滤或提前终止。
    """

    logger.info("=== 调试模式启动：打印模型所有 step() 输出 ===")

    agent = DataAgent(system_prompt=cfg.single.system_prompt)
    agent.update_memory("user", query)

    # 最多执行10步（防止无限循环）
    for step_index in range(1, 6):
        logger.info(f"\n------ Step {step_index} 开始 ------")
        try:
            result = asyncio.run(agent.step())
            logger.info(f"[Step {step_index} 输出]\n{result}\n")

            # 每一步都 yield 出去，方便外部记录
            yield {"step": step_index, "output": result}

        except Exception as e:
            logger.exception(f"Step {step_index} 执行出错: {e}")
            yield {"status": "error", "step": step_index, "reason": str(e)}
            break

    logger.info("=== 调试模式结束 ===")
    yield {"status": "done"}
    return "completed"

def main(query: str, config: Dict[str, Any] | None = None) -> Generator[Dict[str, Any], None, str]:
    """
    配置解析、进行任务模式选择、生成流失输出
    """
    cfg = OrchestrationConfig.model_validate(config or {})
    logger.info(f"Orchestration mode={cfg.mode}")
    if cfg.mode == "single":
        return (yield from _run_single(query, cfg))
    else:
        raise ValueError(f"Invalid mode: {cfg.mode}")

def test():
    cfg = OrchestrationConfig.model_validate({
        "mode": "single",
        "rag": {
            "collection_name": "japan_shrimp",
            "topk_single": 5,
        },
        "single": {
            "temperature": 0.4,
            "max_tokens": 4096
        }
    })
    for info in _run_single("请解释一下循环水养殖系统的原理", cfg):
        print(info)

if __name__ == "__main__":
    test()