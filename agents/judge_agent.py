from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from dotenv import load_dotenv
from agents import SummarizeAgent,ChatRAGAgent
import os
import json
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("JudgeAgent")
logger.setLevel(logging.INFO)
class JudgeAgent:
    def __init__(self):
        self.load_env()
        self.load_config()
        self.init_agents()

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
    
    def init_agents(self):
        """初始化回答和判断智能体"""
        self.agent = ChatAgent(
            system_message=(
                "你是一个善于判断回答质量的助手，你的任务是判断下面这个回答是否全面、准确和合理地回答了用户提出的问题。"
            ),
            model=ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI,
                model_type=ModelType.GPT_4O_MINI,
                api_key=self.api_key,
                model_config_dict={"temperature": 0.4, "max_tokens": 4096},
            )
        )
    def run(self, query: str, answer: str):
        """执行回答流程"""
        chat_agent = ChatRAGAgent()
        chat_result = chat_agent.chat(query)
        summarize_agent = SummarizeAgent()
        output = summarize_agent.reponse_agent(query, answer, chat_result)
        return output
    
    def judge(self, query: str, answer: str) -> bool:
        """返回是否满足需求，True表示回答满意"""
        judgement_prompt = (
            f"用户的问题是：{query}\n"
            f"回答是：{answer}\n"
            f"如果需要再进行深度讨论和进一步检索等方法请回复：'NO'。如果答案已经非常详细并且全面准确解决了问题，请回复：'YES'.如果回答'YES'首先需要确保用户的问题非常非常简单并且回答的过程不需要推理不需要思考。否则请回答'NO'。请只回答YES或NO，不要解释。"
        )
        #response = self.agent.step(judgement_prompt)
        #result = response.msg.content.strip().upper()
        result = "NO"
        if result == "YES":
            logger.info("判断结果：单智能体回答已满足问题需求")
            return answer
        elif result == "NO":
            logger.info("判断结果：需要多智能体进行进一步分析")
            output = self.run(query, answer)
            return output
        else:
            logger.info(f"判断结果:{result}，回答不符合格式，返回单智能体答案。")
            return answer
    

