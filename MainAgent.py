from retrievers import ModelManager
from agents import AgentWithRAG, JudgeAgent
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MainAgent")
logger.setLevel(logging.INFO)

def preload_models():
    """预热模型"""
    logger.info("正在预热模型...")
    model_manager = ModelManager()
    model_manager.get_embedding_model()
    logger.info("模型预热完成！")

def simple_agent(query: str):
    """单智能体"""
    # 加载模型
    preload_models()
    # 创建单智能体
    chat_agent = AgentWithRAG()
    output = chat_agent.run(query)
    return output

def judge_agent(query: str, answer: str):
    """判断是否需要启用多智能体写作场景"""
    judge_agent = JudgeAgent()
    result = judge_agent.judge(query, answer)
    return result

def main():
    query = input("请输入问题:")
    answer1 = simple_agent(query)
    logger.info(f"单智能体的初步回答：{answer1}")
    answer2 = judge_agent(query, answer1)
    print(answer2)

if __name__ == "__main__":
    main()
    