from agents import ChatMultiAgent
from agents import SummarizeAgent
from retrievers import ModelManager
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

def main(query: str):
    """主函数"""
    # 加载模型
    preload_models()
    # 创建多智能体聊天系统
    chat_agent = ChatMultiAgent()
    chat_result = chat_agent.run(query)
    summarize_agent = SummarizeAgent()
    output = summarize_agent.reponse_agent(query, chat_result)
    return output

if __name__ == "__main__":
    query = input("请输入问题:")
    answer = main(query)
    print(answer)
    
 


