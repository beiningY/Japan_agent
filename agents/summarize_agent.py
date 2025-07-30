from agents.plan_agent import PlanAgent
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from dotenv import load_dotenv
import os
import json
import logging
#问题+讨论+评论+建议
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
            system_message="你是一个擅长总结并回答问题的专家，你的任务是根据用户的问题参考两种不同的答案，总结并给出最终的最准确的答案。",
            model=ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI,
                model_type=ModelType.GPT_4O_MINI,
                api_key=self.api_key,
                model_config_dict={"temperature": 0.4, "max_tokens": 4096},
            )
        )

    def reponse_agent(self, query, answer, chat_result):
        input = f"""用户的问题是：{query}
单智能体的回答是：{answer}
养殖员和专家顾问讨论的对话是：{chat_result}
请你参考单智能体和讨论对话两种不同的回答。你需要根据用户的问题总结并给出最终最准确的答案
切记你是一个对于陆上循环水养殖南美白对虾系统的专家。问题的答案请围绕这个主题展开回答，一定要抓取对话中的对答案有帮助的真实检索到的信息，一定要确保数据准确有源头。如果场景对话的内容偏离用户问题主题就忽略，参考单智能体的回答。
"""
        response = self.agent.step(input)
        return response.msg.content
if __name__ == "__main__":
    Agent = SummarizeAgent()
    query = input("请输入问题：")
    answer = input("请输入答案：")
    chat_result = input("请输入对话：")
    result = Agent.reponse_agent(query, answer, chat_result)
    print(result)
