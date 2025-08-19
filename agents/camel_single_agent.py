from agents.base import BaseAgent
import logging
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from rag.camel_rag import RAG

logger = logging.getLogger("CamelSingleAgent")
logger.setLevel(logging.INFO)
class CamelSingleAgent(BaseAgent):
    r"""
    Camel框架的单智能体对话，支持使用RAG增强检索后的相关知识，给出专业的回答。
    """
    def __init__(self,
                 collection_name: str | None = None,
                 rag: bool = True,
                 **kwargs):
        super().__init__(**kwargs) 
        self.custom_collection_name = collection_name
        if rag:
            self.rag = RAG(self.custom_collection_name or self.config.get("collection_name"))
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
        context = self.rag.rag_retrieve(query, topk or self.config.get("vector_top_k", 5))
        rag_contexts = (
            f"用户的问题是: {query}\n"
            f"相关知识内容如下，请结合以下信息作答，如果信息与问题无关可忽略：\n"
            + "\n".join(context) +
            "\n如果记忆的上下文被截断请无视，必须根据用户问题和可参考的知识库内容给出合理的答案。"
        )
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
