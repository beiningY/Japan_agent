from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.messages import BaseMessage
from camel.societies import RolePlaying 
from rag_pipeline.camel_rag import RAG
import logging
import re
from agents.base import BaseAgent

logger = logging.getLogger("CamelRoleplayAgent")

class CamelRoleplayAgent(BaseAgent):
    r"""
    Camel框架的角色扮演对话，支持使用RAG增强检索后的相关知识，给出专业的讨论。
    """
    def __init__(self,
                 user_role_name: str | None = None,
                 assistant_role_name: str | None = None,
                 with_task_specify: bool | None = None,
                 with_task_planner: bool | None = None,
                 collection_name: str | None = None,
                 **kwargs):
        self.custom_user_role_name = user_role_name
        self.custom_assistant_role_name = assistant_role_name
        self.custom_with_task_specify = with_task_specify
        self.custom_with_task_planner = with_task_planner
        self.custom_collection_name = collection_name
        super().__init__(**kwargs)
        self.rag = RAG(self.custom_collection_name or self.config.get("collection_name"))


    def init_model(self):
        """初始化模型"""
        self.model=ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI,
                model_type=ModelType.GPT_4O_MINI,
                api_key=self.api_key,
                model_config_dict={"temperature": self.temperature, "max_tokens": self.max_tokens},
            )

    def create_society(self, query: str):
        """创建助手角色参数"""
        assistant_role_kwargs = {
            'assistant_role_name': self.custom_assistant_role_name,
            'assistant_agent_kwargs': {
                'model': self.model
            }
        }
        """创建用户角色参数"""
        user_role_kwargs = {
            'user_role_name': self.custom_user_role_name,
            'user_agent_kwargs': {
                'model': self.model
            }
        }

        """创建批评角色参数
        critic_role_kwargs = {
            'with_critic_in_the_loop': self.custom_with_critic_in_the_loop if self.custom_with_critic_in_the_loop is not None else False,
            'critic_role_name': self.custom_critic_role_name or '农业专家',
            'critic_kwargs': {'model': self.model},
            'critic_criteria': '是否符合农业专家的角色'
        }        
        """

        """创建细化任务参数"""
        task_special_kwargs = {
            'with_task_specify': self.custom_with_task_specify if self.custom_with_task_specify is not None else False,
            'task_specify_agent_kwargs': {
                'model': self.model,
            }
        }   
        """创建计划任务参数"""
        task_plan_kwargs = {
            'with_task_planner': self.custom_with_task_planner if self.custom_with_task_planner is not None else False,
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
            #**critic_role_kwargs,
            **task_special_kwargs,   
            **task_plan_kwargs,
            **task_kwargs
        )
        return society
    
    def rag_context(self, query: str, topk: int | None = None):
        # 取出Instruction部分（核心问题）
        instruction_match = re.search(r'Instruction:\s*(.*)', query, re.DOTALL)
        if instruction_match:
            question = instruction_match.group(1).strip()
        else:
            question = query.strip()

        # 单轮/多轮不同topk
        topk = topk if topk is not None else self.config.get("vector_top_k", 5)
        context = self.rag.rag_retrieve(question, topk)
        rag_contexts = (
            f"用户的问题是: {question}\n"
            f"相关知识内容如下，请结合以下信息作答，如果信息与问题无关可忽略：\n"
            + "\n".join(context) +
            "\n如果记忆的上下文被截断请无视，必须根据用户问题和可参考的知识库内容给出合理的答案。"
        )
        return rag_contexts


    def stream(self, query: str, round_limit: int = 5):
        """主对话逻辑流式输出：RAG增强的多轮用户-专家角色扮演对话"""
        society = self.create_society(query)
        input_msg = society.init_chat()
        output_msg = f"""开始进入多轮对话场景模式......
主任务设定：\n{query}
对话场景用户角色: {society.user_agent.role_name}
对话场景专家角色: {society.assistant_agent.role_name}
"""     
        data = {
            "agent_type": "chat_agent",
            "agent_response": output_msg
        }
        yield data
        # 进行多轮对话循环
        for round_idx in range(1, round_limit + 1):
           
            # 由User Agent拆分问题
            _, user_response = society.step(input_msg)
            user_content = user_response.msg.content.strip()
            data = {
                "agent_type": "chat_agent",
                "agent_response": user_content,
                "role_name": society.user_agent.role_name
            }
            yield data
            if user_response.terminated or "CAMEL_TASK_DONE" in user_content:
                break
            if "CAMEL_TASK_DONE" in user_response.msg.content:
                break
            # 调用RAG补充prompt 新建拼接Assistant Agent消息
            assistant_input = self.rag_context(user_content)
            assistant_msg = BaseMessage.make_assistant_message(
                role_name=society.assistant_agent.role_name,
                content=assistant_input,
            )

            assistant_response, _ = society.step(assistant_msg)
            assistant_content = assistant_response.msg.content.strip()
            data = {
                "agent_type": "chat_agent",
                "agent_response": assistant_content,
                "role_name": society.assistant_agent.role_name
            }
            yield data

            if assistant_response.terminated:
                break
            if "CAMEL_TASK_DONE" in assistant_response.msg.content:
                break
            # 准备下一轮输入
            input_msg = assistant_response.msg
        return
    
    def run(self, query: str, round_limit: int = 5):
        """输出完后返回全部对话的过程"""
        output_msg = ""
        for i in self.stream(query, round_limit):
            output_msg += i["agent_response"]
        return output_msg




