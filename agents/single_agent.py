from agents.base import BaseAgent
import logging
from rag.lang_rag import LangRAG
from concurrent.futures import Future
import os
from openai import OpenAI
from agents.sql_agent import main as sql_agent
import asyncio
import time
logger = logging.getLogger("SingleAgent")
logger.setLevel(logging.INFO)
class SingleAgent(BaseAgent):
    def __init__(self,
                 collection_name: str | None = None,
                 rag: bool = True,
                 **kwargs):
        super().__init__(**kwargs) 
        self.custom_collection_name = collection_name
        if rag:
            self.rag = LangRAG(
                persist_path="data/vector_data",
                collection_name=self.custom_collection_name or self.config.get("collection_name")
            )
        else:
            self.rag = None
    def init_model(self):
        """初始化Camel Single Agent模型"""
        self.agent = OpenAI(api_key=self.api_key)

    def rag_context(self, query: str, topk: int | None = None):
        """获取RAG增强检索后的chunk并合并成context"""
        contexts = self.rag.retrieve(query, k=topk or self.config.get("vector_top_k", 5))
        logger.info(f"检索到的是{contexts}")
        if not contexts:
            answer = "抱歉，知识库中未找到相关信息。"
            logger.info(f"回答: {answer}")
            return answer
        return self._build_rag_context_from_docs(contexts, query)

    def _build_rag_context_from_docs(self, contexts, query: str) -> str:
        """根据检索到的文档构建 prompt 上下文"""
        content = "\n\n".join([f"片段{i+1}: {doc.page_content}" for i, doc in enumerate(contexts)])
        try:
            sources = list(set([doc.metadata.get("source", "未知来源") for doc in contexts]))
        except Exception as e:
            logger.warning(f"提取文档来源时出错: {e}")
            sources = ["未知来源"]

        rag_contexts = (
            f"问题：{query}\n\n"
            f"参考内容：\n{content}\n\n"
            f"请务必说明参考了以下文件：{', '.join(sources)}"
            f"如果记忆的上下文被截断请无视，必须根据用户问题和可参考的知识库内容给出合理的答案。"
        )
        return rag_contexts


    def run(self, query: str, topk: int | None = None):
        """执行一次查询 返回agent查询后的结果"""
        if self.rag:
            context = self.rag_context(query, topk)
        else:
            context = query
        response = self.agent.responses.create(
            model="gpt-4o",
            instructions=self.system_message,
            input=context,
        )
        result = response.output_text
        return result
    
    def stream(self, query: str, topk: int | None = None):
        """流式输出查询结果（在 RAG 步骤使用队列 + Future，先发送排队状态）"""
        if not self.rag:
            # 无 RAG，直接执行
            result = self.run(query, topk)
            yield {
                "agent_type": "single_agent_rag",
                "agent_response": result
            }
            return

        # 1) 提交 RAG 检索任务（异步）
        request_id, future = self.rag.retrieve_async(query, k=topk or self.config.get("vector_top_k", 5))

        # 2) 先向上游发送“排队中”事件
        yield {
            "agent_type": "single_agent_rag",
            "status": "queued",
            "request_id": request_id,
            "message": "RAG 检索任务已排队，等待执行"
        }

        # 3) 等待 RAG 检索完成，构建上下文并调用 LLM
        contexts = future.result()
        yield {
            "agent_type": "single_agent_rag",
            "status": "started",
            "request_id": request_id,
            "message": "RAG 检索 已完成"
        }
        if not contexts:
            # 无检索结果也要给出可读回复
            logger.info("抱歉，知识库中未找到相关信息。")
            prompt_context = "抱歉，知识库中未找到相关信息。"
        else:
            logger.info(f"检索到的是{contexts}")
            prompt_context = self._build_rag_context_from_docs(contexts, query)
        start_time = time.time()
        # 用流式接口
        with self.agent.responses.stream(
            model="gpt-4o",
            instructions=self.system_message,
            input=prompt_context,
        ) as stream:

            buffer = ""  # 拼接完整文本
            for event in stream:
                if event.type == "response.output_text.delta":
                    buffer += event.delta
                    yield {
                        "agent_type": "single_agent_rag",
                        "status": "in_progress",
                        "request_id": request_id,
                        "agent_response": event.delta   
                    }

                elif event.type == "response.completed":
                    end = time.time()
                    logger.info(f"openai响应时间: {end - start_time}秒")
                    # 返回最终完整结果
                    yield {
                        "agent_type": "single_agent_rag",
                        "status": "completed",
                        "request_id": request_id,
                        "agent_response": buffer
                    }