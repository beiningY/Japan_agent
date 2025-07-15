from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from dotenv import load_dotenv
import os
import json
import logging
from retrievers import RAG

logger = logging.getLogger("AgentWithRAG")


class AgentWithRAG:
    def __init__(self):
        self.load_env()
        self.load_config()
        self.init_agent()
        self.rag = RAG(self.config.get("collection_name"))
    def load_env(self):
        """加载环境变量"""
        load_dotenv(dotenv_path=".env")
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        self.api_key = os.getenv("GPT_API_KEY")
        if not self.api_key:
            raise ValueError("API_KEY 未在 .env 文件中设置")
            
        os.environ["OPENAI_API_KEY"] = self.api_key

    def load_config(self):
        """加载配置文件"""
        with open("utils/config.json", "r", encoding="utf-8") as f:
            self.config = json.load(f)     
    
    def init_agent(self):
        self.agent = ChatAgent(
            system_message="你是一个南美白对虾的养殖专家，你的任务是根据用户的问题，结合养殖手册和操作日志，给出专业的养殖建议。",
            model=ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI,
                model_type=ModelType.GPT_4O_MINI,
                api_key=self.api_key,
                model_config_dict={"temperature": 0.4, "max_tokens": 4096},
            )
        )
    def rag_context(self, query: str):
        context = self.rag.rag_retrieve(query)
        query = query + "\n相关信息有：\n" + "\n".join(context)
        return query



if __name__ == "__main__":
    agent = AgentWithRAG()
    query = input("请输入问题：")
    context = agent.rag_context(query)
    response = agent.agent.step(context)
    result = response.msg.content
    print(result)
    logger.info(result)