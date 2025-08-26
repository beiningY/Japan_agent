from agents.base import BaseAgent
import logging
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from rag.camel_rag import CamelRAG
from rag.lang_rag import LangRAG
import os
from rag.data_with_mcp import main as db
logger = logging.getLogger("CamelSingleAgent")
logger.setLevel(logging.INFO)
class CamelSingleAgent(BaseAgent):
    r"""
    Camel框架的单智能体对话，支持使用RAG增强检索后的相关知识，给出专业的回答。
    """
    def __init__(self,
                 collection_name: str | None = None,
                 rag: bool = True,
                 data_with_mcp: bool = False,
                 **kwargs):
        super().__init__(**kwargs) 
        self.custom_collection_name = collection_name
        self.data_with_mcp = data_with_mcp
        if rag:
            self.rag = LangRAG(
                persist_path="data/vector_data",
                collection_name=self.custom_collection_name or self.config.get("collection_name")
            )
        else:
            self.rag = None
    def init_model(self):
        """初始化Camel Single Agent模型"""
        self.agent = ChatAgent(
            system_message=self.system_message,
            model=ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI,
                model_type=ModelType.GPT_4O_MINI,
                api_key=self.api_key,
                model_config_dict={"temperature": self.temperature, "max_tokens": self.max_tokens},
            )
        )

    def rag_context(self, query: str, topk: int | None = None):
        """获取RAG增强检索后的chunk并合并成context"""
        contexts = self.rag.retrieve(query, k=topk or self.config.get("vector_top_k", 5))
        logger.info(f"检索到的是{contexts}")
        if not contexts:
            answer = "抱歉，知识库中未找到相关信息。"
            logger.info(f"回答: {answer}")
            return answer

        # 提取唯一源文件（兼容 Document 与 str）
        def _extract_source(item):
            try:
                if hasattr(item, "metadata") and isinstance(item.metadata, dict):
                    return os.path.basename(item.metadata.get("source", "未知文件"))
            except Exception:
                pass
            return "无源文件信息"

        sources = list(set([_extract_source(doc) for doc in contexts]))

        # 生成内容（兼容 Document 与 str）
        def _to_text(item):
            return item.page_content if hasattr(item, "page_content") else str(item)

        content = "\n".join([f"{i+1}. {_to_text(ctx)}" for i, ctx in enumerate(contexts)])
        rag_contexts = (
            f"问题：{query}\n\n"
            f"参考内容：\n{content}\n\n"
            f"请务必说明参考了以下文件：{', '.join(sources)}"
            f"如果记忆的上下文被截断请无视，必须根据用户问题和可参考的知识库内容给出合理的答案。"
        )
        if self.data_with_mcp:
            db_response = db(query)
            rag_contexts = f"{rag_contexts}\n\n以下是查询数据库后给出的数据和答案，请参考：\n{db_response}"
        return rag_contexts


    def run(self, query: str, topk: int | None = None):
        """执行一次查询 返回agent查询后的结果"""
        if self.rag:
            context = self.rag_context(query, topk)
        else:
            context = query
        response = self.agent.step(context)
        result = response.msg.content
        if self.rag:
            self.rag.release()
        return result
    
    def stream(self, query: str, topk: int | None = None):
        """流式输出查询结果"""
        result = self.run(query, topk)
        yield {
            "agent_type": "single_agent_rag",
            "agent_response": result
        }
