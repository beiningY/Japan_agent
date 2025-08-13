from __future__ import annotations
import logging
from typing import Any, Dict, Generator, Optional
from pydantic import BaseModel, Field
from agents import CamelSingleAgent, CamelRoleplayAgent

logger = logging.getLogger("Orchestrator")

class RAGConfig(BaseModel):
    """
    RAGConfig 配置类，用于配置 RAG 相关参数
    """
    collection_name: Optional[str] = "all_data"
    topk_single: Optional[int] = 5
    topk_multi: Optional[int] = 5


class SingleTurnConfig(BaseModel):
    """
    对于single agent进行配置和选择
    """
    temperature: Optional[float] = 0.4
    system_prompt: Optional[str] = "你是一个领域专家，你的任务是根据用户的问题，结合增强检索后的相关知识，给出专业的回答。"
    max_tokens: Optional[int] = 4096


class RoleplayTurnConfig(BaseModel):
    """
    对于multi agent进行配置和选择
    """    
    temperature: Optional[float] = 0.4
    user_role_name: Optional[str] = "user"
    assistant_role_name: Optional[str] = "assistant"
    round_limit: int = 5
    max_tokens: Optional[int] = 10000
    with_task_specify: Optional[bool] = False
    with_task_planner: Optional[bool] = False

class AutoTurnConfig(BaseModel):
    """
    对于auto agent进行配置和选择
    """
    temperature: Optional[float] = 0.4
    system_prompt: Optional[str] = "你是一个领域专家，你的任务是根据用户的问题，结合增强检索后的相关知识，给出专业的回答。"
    max_tokens: Optional[int] = 4096


class OrchestrationConfig(BaseModel):
    """
    对于传入的参数进行配置解析
    """
    # mode: auto -> (single -> judge -> roleplay -> summarize), single, roleplay
    mode: str = "auto"
    rag: RAGConfig = Field(default_factory=RAGConfig)
    single: SingleTurnConfig = Field(default_factory=SingleTurnConfig)
    roleplay: RoleplayTurnConfig = Field(default_factory=RoleplayTurnConfig)


def _run_single(query: str, cfg: OrchestrationConfig) -> Generator[Dict[str, Any], None, str]:
    """
    生成调用RAG的单轮对话的流式输出
    """
    agent = CamelSingleAgent(
        temperature=cfg.single.temperature,
        system_message=cfg.single.system_prompt,
        collection_name=cfg.rag.collection_name,
        model_max_tokens=cfg.single.max_tokens,
    )
    result = yield from agent.stream(query, topk=cfg.rag.topk_single)
    return result
def _run_roleplay(query: str, cfg: OrchestrationConfig) -> Generator[Dict[str, Any], None, str]:
    """
    生成调用RAG的单轮对话的流式输出
    """
    agent = CamelRoleplayAgent(
        temperature=cfg.roleplay.temperature,
        user_role_name=cfg.roleplay.user_role_name,
        assistant_role_name=cfg.roleplay.assistant_role_name,
        round_limit=cfg.roleplay.round_limit,
        model_max_tokens=cfg.roleplay.max_tokens,
        with_task_specify=cfg.roleplay.with_task_specify,
        with_task_planner=cfg.roleplay.with_task_planner,
        collection_name=cfg.rag.collection_name,
    )
    result = yield from agent.stream(query, topk=cfg.rag.topk_multi)
    return result

def _run_auto(query: str, cfg: OrchestrationConfig) -> Generator[Dict[str, Any], None, str]:
    """
    生成多智能体协作的单多轮对话的流式输出
    """
    # 1) single
    single_answer = yield from _run_single(query, cfg)
    # 2) judge
    judge = CamelSingleAgent(
        rag=False,
        temperature=cfg.auto.temperature,
        system_message=cfg.auto.system_prompt,
        model_max_tokens=cfg.auto.max_tokens
    )
    # 3) summarize
    summarize = CamelSingleAgent(
        rag=False,
        temperature=cfg.auto.temperature,
        system_message=cfg.auto.system_prompt,
        model_max_tokens=cfg.auto.max_tokens
    )



    final_answer = yield from judge.judge(query, single_answer, round_limit=cfg.multi.round_limit)
    return final_answer


def main(query: str, config: Dict[str, Any] | None = None) -> Generator[Dict[str, Any], None, str]:
    """
    配置解析、进行任务模式选择、生成流失输出
    """
    cfg = OrchestrationConfig.model_validate(config or {})
    logger.info(f"Orchestration mode={cfg.mode}")
    if cfg.mode == "single":
        return (yield from _run_single(query, cfg))
    elif cfg.mode == "multi":
        return (yield from _run_roleplay(query, cfg))
    elif cfg.mode == "auto":
        return (yield from _run_auto(query, cfg))
    else:
        raise ValueError(f"Invalid mode: {cfg.mode}")

