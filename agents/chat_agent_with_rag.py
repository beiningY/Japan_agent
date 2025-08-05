import os
import json
from dotenv import load_dotenv
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.messages import BaseMessage
from camel.societies import RolePlaying 
from rag_pipeline.handle_rag.vector_retriever import RAG
import logging
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ChatAgentRag")
logger.setLevel(logging.INFO)
class ChatRAGAgent:
    def __init__(self):
        self.load_env()
        self.load_config()
        self.init_models()
        self.rag = RAG(self.config.get("collection_name"))

    def load_env(self):
        """加载环境变量"""
        load_dotenv(dotenv_path=".env")
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        self.api_key = os.getenv("GPT_API_KEY")
        if not self.api_key:
            raise ValueError("错误：API_KEY 未在 .env 文件中或环境变量中设置。")
        os.environ["OPENAI_API_KEY"] = self.api_key

   
    def load_config(self):
        """加载配置文件"""
        with open("utils/config.json", "r", encoding="utf-8") as f:
            self.config = json.load(f)  


    def init_models(self):
        """初始化模型"""
        self.model=ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI,
                model_type=ModelType.GPT_4O,
                api_key=self.api_key,
                model_config_dict={"temperature": self.config.get("temperature", 0.4), "max_tokens": self.config.get("max_tokens", 4096)},
            )


    def create_society(self, query: str):

        """创建助手角色参数"""
        assistant_role_kwargs = {
            'assistant_role_name': '南美白对虾养殖专家',
            'assistant_agent_kwargs': {'model': self.model}
        }        
        
        """创建用户角色参数"""
        user_role_kwargs = {
            'user_role_name': '南美白对虾养殖员',
            'user_agent_kwargs': {'model': self.model}
        } 

        """创建批评角色参数"""
        critic_role_kwargs = {
            'with_critic_in_the_loop': True,
            'critic_role_name': '农业专家',
            'critic_kwargs': {'model': self.model},
            'critic_criteria': '是否符合农业专家的角色'
        }        

        """创建细化任务参数"""
        task_special_kwargs = {
            'with_task_specify': True,
            'task_specify_agent_kwargs': {
                'model': self.model,
            }
        }   
        """创建计划任务参数"""
        task_plan_kwargs = {
            'with_task_planner': False,
            'task_planner_agent_kwargs': {
                'model': self.model,
            }
        }   
        """创建任务参数"""
        task_kwargs = {
            'task_prompt': query if query else self.config.get("query", "南美白对虾养殖需要注意什么。"),
            'model': self.model,
            #'sys_msg_generator_kwargs': {
            #},
            #'extend_sys_msg_meta_dicts': {
            #},
            'output_language':'zh',
        }

        society = RolePlaying(
            **assistant_role_kwargs,
            **user_role_kwargs,          
            **critic_role_kwargs,
            **task_special_kwargs,   
            **task_plan_kwargs,
            **task_kwargs
        )
        return society
    
    def rag_context(self, query: str):
        """用RAG检索并拼接上下文"""
        input_match = re.search(r'Input:\s*(.*)', query, re.DOTALL)
        instruction_match = re.search(r'Instruction:\s*(.*?)(?:\s*Input:|$)', query, re.DOTALL)
        
        if input_match and input_match.group(1).strip() != "None":
            rag_query = input_match.group(1).strip()
        elif instruction_match:
            rag_query = instruction_match.group(1).strip()
        else:
            rag_query = query
        
        context = self.rag.rag_retrieve(rag_query)
        rag_contexts = query + "\n相关知识内容如下，请结合以下信息作答，如果信息与问题无关可忽略。：\n" + "\n".join(context)
        return rag_contexts

    def chat(self, query: str, round_limit: int = 5):
        """主对话逻辑：RAG增强的多轮用户-专家角色扮演对话"""
        society = self.create_society(query)
        input_msg = society.init_chat()
        output_msg = f"""任务设定：\n{query}
用户角色: {society.user_agent.role_name}
专家角色: {society.assistant_agent.role_name}
"""
        for round_idx in range(1, round_limit + 1):

            # 用户先提问（由User Agent生成）
            _, user_response = society.step(input_msg)
            user_content = user_response.msg.content.strip()

            if user_response.terminated or "CAMEL_TASK_DONE" in user_content:

                break

            # 调用RAG补充知识后，交由专家回答
            assistant_input = self.rag_context(user_content)
            assistant_msg = BaseMessage.make_assistant_message(
                role_name=society.assistant_agent.role_name,
                content=assistant_input,
            )

            assistant_response, _ = society.step(assistant_msg)
            assistant_content = assistant_response.msg.content.strip()


            if assistant_response.terminated:
                break
            if "CAMEL_TASK_DONE" in user_response.msg.content:
                break
            if "CAMEL_TASK_DONE" in assistant_response.msg.content:
                break
            # 准备下一轮输入
            input_msg = assistant_response.msg
            output_msg += f"第{round_idx}轮养殖员的输出:\n{user_content}\n" + f"第{round_idx}轮专家顾问的输出:\n{assistant_content}\n"
        logger.info(f"最终的对话结果:\n{output_msg}\n")
        return output_msg
    
if __name__ == "__main__":
    Agent = ChatRAGAgent()
    query = input("请输入问题：")
    Agent.chat(query)
