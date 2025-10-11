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

def _run_single(query: str, cfg) -> Generator[Dict[str, Any], None, str]:
    """
    执行 DataAgent 并逐步记录所有输出内容。
    传输过程中的工具调用、思考等有效信息，最终返回答案。
    """
    logger.info("=== 启动 DataAgent 单轮运行 ===")
    logger.info(f"用户输入: {query}")

    # 初始化 Agent
    agent = DataAgent(system_prompt=cfg.single.system_prompt)
    agent.update_memory("user", query)

    step_index = 0
    max_steps = 10
    final_answer = None

    try:
        from agents.core_schema import AgentState
        
        while step_index < max_steps and agent.state != AgentState.FINISHED:
            step_index += 1
            logger.info(f"[Step {step_index}] 开始执行")
            
            try:
                # 执行一步
                result = asyncio.run(agent.step())
                logger.info(f"[Step {step_index}] 完成: {result[:200] if result else 'None'}")
                
                # 获取最新的消息，提取有用信息
                if agent.messages:
                    last_msg = agent.messages[-1]
                    
                    # 如果是工具调用
                    if last_msg.role == "tool":
                        tool_name = last_msg.name or "unknown"
                        yield {
                            "type": "tool_call",
                            "step": step_index,
                            "tool_name": tool_name,
                            "content": f"调用工具: {tool_name}"
                        }
                    
                    # 如果是assistant的思考或回答
                    elif last_msg.role == "assistant" and last_msg.content:
                        content = last_msg.content
                        # 过滤掉内部标记
                        if content not in ("[tools] executing", "[tools_executed]", "Thinking complete - no action needed"):
                            # 检查是否是最终答案
                            if agent.state == AgentState.FINISHED:
                                final_answer = content
                                yield {
                                    "type": "final_answer",
                                    "step": step_index,
                                    "content": content
                                }
                            else:
                                yield {
                                    "type": "thinking",
                                    "step": step_index,
                                    "content": content[:300]  # 限制长度
                                }
                
            except Exception as e:
                logger.exception(f"[Step {step_index}] 执行出错: {e}")
                yield {
                    "type": "error",
                    "step": step_index,
                    "status": "error",
                    "reason": str(e)
                }
                break
        
        # 如果达到最大步数但还没有答案，尝试获取最后的回答
        if not final_answer and agent.messages:
            for msg in reversed(agent.messages):
                if msg.role == "assistant" and msg.content:
                    content = msg.content
                    if content not in ("[tools] executing", "[tools_executed]", "Thinking complete - no action needed"):
                        try:
                            # 检查是否是JSON格式的工具结果
                            import json
                            json.loads(content)
                        except:
                            # 不是JSON，是自然语言回答
                            final_answer = content
                            break
        
        # 返回最终答案
        if final_answer:
            logger.info(f"=== DataAgent 完成，最终答案: {final_answer[:100]}... ===")
            yield {
                "status": "final",
                "answer": final_answer
            }
        else:
            logger.warning("=== DataAgent 执行完毕但未获得明确答案 ===")
            yield {
                "status": "final",
                "answer": "抱歉，未能生成有效回答。"
            }
            
    except Exception as e:
        logger.exception(f"DataAgent 运行异常: {e}")
        yield {
            "status": "error",
            "reason": str(e)
        }
    
    finally:
        # 清理资源
        try:
            asyncio.run(agent.cleanup())
        except:
            pass
    
    return "completed"


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
    
    # 支持 "single" 和 "auto" 模式（都使用single agent）
    if cfg.mode in ("single", "auto"):
        return (yield from _run_single(query, cfg))
    else:
        raise ValueError(f"Invalid mode: {cfg.mode}. Supported modes: 'single', 'auto'")

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