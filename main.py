from agents import ChatMultiAgent
from agents import SummarizeAgent
from retrievers import ModelManager
from agents import AgentWithRAG
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Main")
logger.setLevel(logging.INFO)
def preload_models():
    """预热模型"""
    logger.info("正在预热模型...")
    model_manager = ModelManager()
    model_manager.get_embedding_model()
    logger.info("模型预热完成！")

def advanced_agents(query: str):
    """对话场景智能体"""
    # 加载模型
    preload_models()
    # 创建多智能体聊天系统
    chat_agent = ChatMultiAgent()
    chat_result = chat_agent.run(query)
    summarize_agent = SummarizeAgent()
    output = summarize_agent.reponse_agent(query, chat_result)
    return output

def simple_agents(query: str):
    """单智能体"""
    # 加载模型
    preload_models()
    # 创建多智能体聊天系统
    chat_agent = AgentWithRAG()
    output = chat_agent.run(query)
    return output

if __name__ == "__main__":
    query = input("请输入问题:")
    answer = simple_agents(query)
    print(answer)
    
 


