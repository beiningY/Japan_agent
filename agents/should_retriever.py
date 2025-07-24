import os
import json
from dotenv import load_dotenv
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.agents import ChatAgent
from retrievers import RAG
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ShouldRetriever")
logger.setLevel(logging.INFO)

class ShouldRetrieverResult(BaseModel):
    should_retriever: Optional[bool] = True
    knowledgebase_name: Optional[dict] = {"all_data": 5}

class ShouldRetriever:
    def __init__(self):
        """初始化ShouldRetriever"""
        self.load_env()
        self.load_config()
        self.init_agent()
        self.rag_instances = {}

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
        """初始化ChatAgent"""
        self.agent = ChatAgent(
            system_message="你是一个判断是否需要调用知识库的专家，请根据用户的问题进行判断。",
            model=ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI,
                model_type=ModelType.GPT_4O_MINI,
                api_key=self.api_key,
                model_config_dict={"temperature": 0.4, "max_tokens": 4096},
            )
        )
    
    def get_rag_instance(self, collection_name: str) -> RAG:
        """获取RAG实例，使用缓存避免重复创建"""
        if collection_name not in self.rag_instances:
            logger.info(f"创建新的RAG实例: {collection_name}")
            self.rag_instances[collection_name] = RAG(collection_name=collection_name)
        return self.rag_instances[collection_name]

    def get_should_retriever(self, query: str) -> Optional[Dict[str, Any]]:
        """执行判断是否需要调用知识库"""
        if not query or not query.strip():
            return None
        use_msg = self.retriever_prompt(query)            
        try:
            response = self.agent.step(use_msg)
            content = response.msg.content
            
            # 检查content是否为空
            if not content or not content.strip():
                logger.warning("GPT返回空内容，使用默认配置")
                return self._get_default_should_retriever()
                
            # 尝试解析JSON
            result_dict = json.loads(content)
            result = ShouldRetrieverResult(**result_dict)
            return result.dict()
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误: {e}")
            logger.error(f"GPT返回内容: {content}")
            logger.error("使用默认配置继续...")
            return self._get_default_should_retriever()
            
        except Exception as e:
            logger.error(f"意图识别出错: {e}")
            return self._get_default_should_retriever()
    
    def _get_default_should_retriever(self) -> Dict[str, Any]:
        """获取默认的意图识别结果"""
        return {
            "should_retriever": True,
            "knowledgebase_name": {"all_data": 5}
        }
    def retriever_prompt(self, query: str) -> str:
        return f"""你是一个判断是否需要调用知识库的专家，请根据用户的问题进行判断。

    <should_retriever_list>
    1. 需要调用知识库（如养殖手册、操作日志等）进行回答；
    2. 无需调用知识库，仅依赖已有常识/推理能力回答。
    </should_retriever_list>

    <知识库说明>
    系统知识库分为以下几类：
    - "book_zh"：养殖手册、水循环系统设计和饲料等专业知识；
    - "log"：每日日志、水质数据、关键点总结等；
    - "all_data"：综合养殖手册和操作日志的所有信息。
    </知识库说明>

    <output_format>
    你必须输出 JSON 格式，包含以下字段：
    - "should_retriever": true 或 false；
    - 如果 should_retriever 为 True，则必须包含字段 "knowledgebase_name"，格式为：
    {{"all_data": 5}}
    表示你建议从“all_data”中取5条结果。
    </output_format>

    以下是示例：
    <example>
    问题: 什么是循环水养殖系统？
    输出:
    {{"should_retriever": true, "knowledgebase_name": {{"book_zh": 5}}}}
    问题: 如果今天氨氮为0.06，亚硝酸盐偏高，下一步怎么处理？
    输出:
    {{"should_retriever": true, "knowledgebase_name": {{"all_data": 5}}}}
    </example>

    <question>
    {query}
    </question>
    强调：输出必须是标准 JSON 字典，不要有任何注释或解释。
    """
    def knowledge_context(self, query: str, knowledgebase: Dict[str, int]) -> str:
        """知识库检索并生成提示"""
        if not knowledgebase:
            return ""
        knowledge_context = ""
        for knowledgebase_name, topk in knowledgebase.items():
            rag = self.get_rag_instance(knowledgebase_name)
            retrieved_knowledge = rag.rag_retrieve(query, topk)
            retrieved_content = knowledgebase_name + "：" + "\n".join(retrieved_knowledge)
            if retrieved_content:
                knowledge_context += retrieved_content
                
        return knowledge_context
    

    def generate_prompt(self, query: str, should_retriever_result: Dict[str, Any]) -> str:
        if not should_retriever_result:
            return None

        prompt_parts = "用户的问题是："+query
        should_retriever = should_retriever_result.get("should_retriever")

        # 是否需要知识库
        if should_retriever:
            kb_dict = should_retriever_result.get("knowledgebase_name", {})
            knowledge = self.knowledge_context(query, kb_dict)
            if knowledge:
                prompt_parts += f"相关知识内容如下：\n{knowledge}\n请结合以上信息作答，如果无关可忽略。"

        return prompt_parts

    def process(self, query: str) -> str:
        should_retriever_result = self.get_should_retriever(query)
        result = self.generate_prompt(query, should_retriever_result)
        logger.info("判断是否需要调用知识库结果是："+str(should_retriever_result))
        logger.info("综合提示结果是："+result)
        return result


    