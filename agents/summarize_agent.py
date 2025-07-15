from agents.plan_agent import PlanAgent
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from dotenv import load_dotenv
import os
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SummarizeAgent")
logger.setLevel(logging.INFO)
  
class SummarizeAgent:
    def __init__(self):
        self.plan_agent = PlanAgent()
        self.load_env()
        self.load_config()
        self.init_agent()

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
            system_message="你是一个擅长总结并回答问题的专家，你的任务是根据用户的主问题，通过养殖员和专家顾问的对话形式，总结出最终的答案。",
            model=ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI,
                model_type=ModelType.GPT_4O_MINI,
                api_key=self.api_key,
                model_config_dict={"temperature": 0.4, "max_tokens": 4096},
            )
        )

    def reponse_agent(self, query, chat_result):
        input = f"用户的问题是：{query}，养殖员和专家顾问讨论的对话是：{chat_result}，请你根据用户的问题和养殖员与专家顾问的对话，总结出最终的答案。不用提到对话过程，而是把对话的内容当成是对问题的讨论，如果是跟问题很有关联很有关系的你就总结，如果无关或者不符合回答问题的逻辑的你就忽略。切记你是一个对于陆上循环水养殖南美白对虾系统的专家。问题的答案请围绕这个主题展开回答，一定要抓取对话中的对答案有帮助的真实检索到的信息，一定要确保数据准确。"
        response = self.agent.step(input)
        return response.msg.content
