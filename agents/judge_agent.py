from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from dotenv import load_dotenv
from agents import SummarizeAgent
from typing import Generator, Any, Dict
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
    def __init__(self,
                 rag_collection_name: str | None = None,
                 rag_topk_multi: int | None = None,
                 temperature: float | None = None,
                 multi_user_role_name: str | None = None,
                 multi_assistant_role_name: str | None = None,
                 multi_critic_role_name: str | None = None,
                 with_critic_in_the_loop: bool | None = None,
                 with_task_specify: bool | None = None,
                 with_task_planner: bool | None = None,
                 multi_max_tokens: int | None = None,
                 ):
        self.custom_rag_collection_name = rag_collection_name
        self.custom_rag_topk_multi = rag_topk_multi
        self.custom_temperature = temperature
        self.custom_multi_user_role_name = multi_user_role_name
        self.custom_multi_assistant_role_name = multi_assistant_role_name
        self.custom_multi_critic_role_name = multi_critic_role_name
        self.custom_with_critic_in_the_loop = with_critic_in_the_loop
        self.custom_with_task_specify = with_task_specify
        self.custom_with_task_planner = with_task_planner
        self.custom_multi_max_tokens = multi_max_tokens
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
        temperature = self.custom_temperature if self.custom_temperature is not None else 0.4
        self.agent = ChatAgent(
            system_message=(
                "你是一个善于判断回答质量的助手，你的任务是判断下面这个回答是否全面、准确和合理地回答了用户提出的问题。"
            ),
            model=ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI,
                model_type=ModelType.GPT_4O,
                api_key=self.api_key,
                model_config_dict={"temperature": temperature, "max_tokens": 4096},
            )
        )
    def run(self, query: str, answer: str, round_limit: int = 5) -> Generator[Dict[str, Any], None, str]:
        """执行回答流程"""
        chat_agent = ChatRAGAgent(
            temperature=self.custom_temperature,
            user_role_name=self.custom_multi_user_role_name,
            assistant_role_name=self.custom_multi_assistant_role_name,
            critic_role_name=self.custom_multi_critic_role_name,
            with_critic_in_the_loop=self.custom_with_critic_in_the_loop,
            with_task_specify=self.custom_with_task_specify,
            with_task_planner=self.custom_with_task_planner,
            collection_name=self.custom_rag_collection_name,
            rag_topk_multi_turn=self.custom_rag_topk_multi,
            max_tokens=self.custom_multi_max_tokens,
        )
        chat_result = yield from chat_agent.chat(query, round_limit=round_limit)
        logger.info(f"已完成多轮对话 结果是{chat_result}\n")
        summarize_agent = SummarizeAgent()

        output = summarize_agent.reponse_agent(query, answer, chat_result)
        logger.info(f"已完成总结 结果是{output}\n")
        data = {
            "agent_type": "summarize_agent",
            "agent_response": output
        }
        yield data
        return output
    
    def judge(self, query: str, answer: str, round_limit: int = 5) -> Generator[Dict[str, Any], None, str]:
        """返回是否满足需求，True表示回答满意"""
        judgement_prompt = (
            f"用户的问题是：{query}\n"
            f"回答是：{answer}\n"
            f"如果需要再进行深度讨论和进一步检索等方法请回复：'NO'。如果答案已经非常详细并且全面准确解决了问题，请回复：'YES'.如果回答'YES'首先需要确保用户的问题非常非常简单并且回答的过程不需要推理不需要思考。否则请回答'NO'。请只回答YES或NO，不要解释。"
        )
        response = self.agent.step(judgement_prompt)

        result = response.msg.content.strip().upper()
        logger.info(f"判断结果:{result}")
        if result == "YES":
            data = {
                "agent_type": "judge_agent",
                "agent_response": "\n\n无需启用多轮场景对话，单智能体回答已满足问题需求\n\n"
            }
            yield data
            logger.info("判断结果：单智能体回答已满足问题需求")
            return answer
        elif result == "NO":
            data = {
                "agent_type": "judge_agent",
                "agent_response": "\n\n问题被归类为复杂问题，将启用多轮场景对话模式进行辅助分析\n\n"
            }
            yield data
            logger.info("判断结果：需要多智能体进行进一步分析")
            output = yield from self.run(query, answer, round_limit=round_limit)
            return output
        else:
            data = {
                "agent_type": "judge_agent",
                "agent_response": "\n\njudge_agent: 判断结果不符合格式\n\n"
            }
            yield data
            logger.info(f"判断结果:{result}，回答不符合格式，返回单智能体答案。")
            return answer
    

