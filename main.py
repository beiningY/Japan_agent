from agents import ChatMultiAgent
from agents import SummarizeAgent
from retrievers import ModelManager

def preload_models():
    """预热模型"""
    print("正在预热模型...")
    model_manager = ModelManager()
    model_manager.get_embedding_model()
    print("模型预热完成！")

def main(query: str):
    """主函数"""
    # 加载模型
    preload_models()
    # 创建多智能体聊天系统
    chat_agent = ChatMultiAgent()
    # query = input("请输入问题:")
    chat_result = chat_agent.run(query)
    # 创建总结智能体
    summarize_agent = SummarizeAgent()
    output = summarize_agent.reponse_agent(query, chat_result)
    # print(output)
    return output

if __name__ == "__main__":
    query = input("请输入问题:")
    answer = main(query)
    print(answer)
    
 


