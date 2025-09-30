from __future__ import annotations
from utils.logger import get_logger
import asyncio
from typing import Any, Dict, Generator, Optional
from pydantic import BaseModel, Field
from agents import DataAgent
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



def _run_single(query: str, cfg: OrchestrationConfig) -> Generator[Dict[str, Any], None, str]:
    """
    使用新的 DataAgent（MCP ToolCall）执行任务，仅在结束时返回最终答案。
    不依赖 AgentState，固定小步数执行，避免无限循环。
    """
    agent = DataAgent(system_prompt=cfg.single.system_prompt)
    agent.update_memory("user", query)

    last_step_text: Optional[str] = None
    # 固定最多执行8步，防止任何情况下的无限循环，给足够时间生成最终答案
    tool_call_count = 0
    for step_index in range(1, 8 + 1):
        try:
            last_step_text = asyncio.run(agent.step())

            # 计算工具调用次数
            current_tool_calls = len([m for m in agent.messages if m.role == "tool"])
            if current_tool_calls > tool_call_count:
                tool_call_count = current_tool_calls
                logger.info(f"完成第{tool_call_count}次工具调用")

            # 仅当返回的内容不是占位提示时才认为得到最终答案
            if last_step_text:
                normalized = (last_step_text or "").strip()
                if normalized == "[tools_executed]":
                    logger.info("检测到工具执行完成标记，继续让LLM生成总结")
                    continue
                elif normalized and normalized not in ("Thinking complete - no action needed", "[tools] executing"):
                    # 检查是否是工具调用结果的JSON，如果是则继续执行让LLM总结
                    try:
                        import json
                        parsed = json.loads(normalized)
                        if isinstance(parsed, dict):
                            # 检测各种类型的工具调用结果
                            if "chunks" in parsed:
                                logger.info("检测到检索工具调用返回的结果，继续执行让LLM进行总结")
                                continue
                            elif "status" in parsed or "result" in parsed or "tables" in parsed:
                                logger.info("检测到其他工具调用返回的结果，继续执行让LLM进行总结")
                                continue
                    except (json.JSONDecodeError, TypeError):
                        pass
                    # 如果不是JSON格式的工具结果，认为是最终答案
                    logger.info("检测到LLM生成的自然语言回答")
                    break
        except Exception as e:
            logger.exception("Agent step 执行失败")
            yield {"status": "error", "reason": str(e)}
            break

    # 查找最终回答
    final_answer: Optional[str] = None
    try:
        for m in reversed(agent.messages):
            if (m.role == "assistant" and m.content and
                m.content.strip() not in ("[tools] executing", "Thinking complete - no action needed")):
                content = m.content.strip()
                # 确保不是工具调用的JSON结果
                try:
                    import json
                    parsed = json.loads(content)
                    if isinstance(parsed, dict) and "chunks" in parsed:
                        continue  # 跳过工具调用结果
                except (json.JSONDecodeError, TypeError):
                    pass
                final_answer = content
                break
    except Exception:
        pass

    # 如果仍然没有合适答案，强制模型生成最终回答
    if not final_answer or final_answer.startswith("{"):
        try:
            # 添加明确的总结请求
            agent.update_memory("user", "请根据上述检索到的信息，用中文给出专业的最终回答。不要返回JSON格式，直接给出自然语言回答。")
            summary_result = asyncio.run(agent.step())
            if summary_result and summary_result.strip() not in ("[tools] executing", "Thinking complete - no action needed"):
                final_answer = summary_result.strip()
            else:
                final_answer = "根据检索的信息，我已获得相关数据，但无法生成明确的回答。请查看检索结果或重新提问。"
        except Exception as e:
            logger.exception("生成最终总结失败")
            final_answer = f"处理完成，但生成最终回答时出错：{e}"

    if not final_answer:
        final_answer = "查询已处理完成，但未能生成明确回答。"

    # 仅在结束时返回一次最终答案
    yield {"status": "final", "answer": final_answer}
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

