import os
import json
import re
from dotenv import load_dotenv
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.societies import RolePlaying 
from agents.plan_agent import PlanAgent
from colorama import Fore
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ChatMultiAgent")
logger.setLevel(logging.INFO)
class ChatMultiAgent:
    def __init__(self):
        self.load_env()
        self.load_config()
        self.init_models()
        self.plan_agent = PlanAgent()
          
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
        try:
            with open("utils/config.json", "r", encoding="utf-8") as f:
                self.config = json.load(f)
        except FileNotFoundError:
            logger.warning("未找到 config.json 文件，将使用默认值。")
            self.config = {}


    def init_models(self):
        """初始化模型"""
        self.model=ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI,
                model_type=ModelType.GPT_4O_MINI,
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
        rag_contexts = self.plan_agent.process_query(rag_query)

        return rag_contexts



    def run(self, query: str, chat_turn_limit=10) -> None:
        society = self.create_society(query)
        assiatant_sys_content = society.assistant_sys_msg.content
        #print(Fore.GREEN+ f"助手系统消息:\n{society.assistant_sys_msg}\n")
        #print(Fore.BLUE + f"用户系统消息:\n{society.user_sys_msg}\n")
        #print(Fore.YELLOW + f"原始问题:\n{query}\n")
        #print(Fore.CYAN+ "细化后的问题:"+ f"\n{society.specified_task_prompt}\n")
        n = 0
        input_msg = society.init_chat()
        output_msg = ""
        while n < chat_turn_limit:
            n += 1
            #print(Fore.YELLOW + f"第{n}轮养殖员的输入:\n{input_msg.content}\n")
            _, user_response = society.step(input_msg)
            #print(Fore.GREEN+ f"第{n}轮养殖员的输出:\n{user_response.msg.content}\n")
            input_msg.content += self.rag_context(user_response.msg.content)
            #print(Fore.GREEN+ f"第{n}轮专家顾问的系统消息输入:\n{society.assistant_sys_msg.content}\n")
            if user_response.terminated:
                logger.info(Fore.GREEN+ ("养殖员回答终止的原因: " + f"{user_response.info['termination_reasons']}."))
                break
            assistant_response, user_response2 = society.step(input_msg)
            #print(Fore.BLUE + f"第{n}轮专家顾问的输出:\n{assistant_response.msg.content}\n")
            if assistant_response.terminated:
                logger.info(Fore.GREEN+ ("专家顾问回答终止的原因: " + f"{assistant_response.info['termination_reasons']}."))
                break
            if "CAMEL_TASK_DONE" in user_response.msg.content:
                break
            if "CAMEL_TASK_DONE" in assistant_response.msg.content:
                break
            input_msg = assistant_response.msg
            
            output_msg += f"第{n}轮养殖员的输出:\n{user_response.msg.content}\n" + f"第{n}轮专家顾问的输出:\n{assistant_response.msg.content}\n"
        logger.info(f"最终的对话结果:\n{output_msg}\n")
        return output_msg


