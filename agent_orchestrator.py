from __future__ import annotations
import asyncio
from typing import Any, Dict, Generator, Optional
from pydantic import BaseModel, Field
from agents.single_agent import SingleAgent
from utils.logger import get_logger
logger = get_logger(__name__)

class RAGConfig(BaseModel):
    """
    RAGConfig 配置类，用于配置 RAG 相关参数
    """
    collection_name: Optional[str] = "japan_shrimp"
    topk_single: Optional[int] = 3


class SingleTurnConfig(BaseModel):
    """
    对于single agent进行配置和选择
    """
    system_prompt: Optional[str] = "你是一个查询助手。你可以通过工具查询循环水南美白对虾养殖系统设计及操作手册张驰和ESG综合工程管理文档的内容，也可以通过工具查询sensor_readings表获取传感器数据。请基于工具返回的真实数据回答用户问题，并明确引用来源。"
    model: Optional[str] = "gpt-4o"
    max_steps: Optional[int] = 4


class OrchestrationConfig(BaseModel):
    """
    对于传入的参数进行配置解析
    """

    mode: str = "auto"
    rag: RAGConfig = Field(default_factory=RAGConfig)
    single: SingleTurnConfig = Field(default_factory=SingleTurnConfig)

def _run_single(query: str, cfg) -> Generator[Dict[str, Any], None, str]:
    """
    执行 SingleAgent 并返回结果。
    使用简化的方式直接调用agent.run()获取最终答案。
    """
    logger.info("=== 启动 SingleAgent 单轮运行 ===")
    logger.info(f"用户输入: {query}")

    # 初始化 Agent
    agent = SingleAgent(
        system_prompt=cfg.single.system_prompt,
        model=cfg.single.model,
        max_steps=cfg.single.max_steps
    )

    result = agent.run(query)        
    for event in result:
        yield event


def main(query: str, config: Dict[str, Any] | None = None) -> Generator[Dict[str, Any], None, str]:
    """
    配置解析、进行任务模式选择、生成流式输出
    
    Args:
        query: 用户查询
        config: 配置字典，支持mode字段（"single"或"auto"，默认使用single模式）
    
    Yields:
        包含过程信息和最终答案的字典
    """
    cfg = OrchestrationConfig.model_validate(config or {})
    logger.info(f"Orchestration mode={cfg.mode}")
    
    # 支持 "single" 、 "auto" 和 "roleplay" 模式（都使用single agent）
    if cfg.mode in ("single", "auto", "roleplay"):
        return (yield from _run_single(query, cfg))
    else:
        raise ValueError(f"Invalid mode: {cfg.mode}. Supported modes: 'single', 'auto', 'roleplay'")
