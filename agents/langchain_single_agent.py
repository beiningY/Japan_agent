from agents.base import BaseAgent
from rag_pipeline.lang_rag import LangRAG
from langchain_openai import ChatOpenAI
import os
import logging

logger = logging.getLogger("LangSingleAgent")

class LangchainSingleAgent(BaseAgent):
    def __init__(self,
                 collection_name: str | None = None,
                 **kwargs):
        self.custom_collection_name = collection_name
        super().__init__(**kwargs)
        self.rag = LangRAG(self.custom_collection_name or self.config.get("collection_name"))

    def init_model(self):
        """初始化Langchain Single Agent模型"""
        self.llm = ChatOpenAI(model=self.model_type, temperature=self.temperature, max_tokens=self.max_tokens)



def ask(question: str, k: int = 5):
    """在 main 中实现问答逻辑"""
    kb = LangRAG(
        persist_path="data/vector_data",
        collection_name="bank"
    )

    llm = ChatOpenAI(model="gpt-4o", temperature=0.4, max_tokens=None)
    logger.info(f"\n问题: {question}")
    contexts = kb.retrieve(question, k=k)
    logger.info(f"检索到的是{contexts}")
    if not contexts:
        answer = "抱歉，知识库中未找到相关信息。"
        logger.info(f"回答: {answer}")
        return answer

    # 提取唯一源文件
    sources = list(set([
        os.path.basename(doc.metadata.get("source", "未知文件"))
        for doc in contexts
    ]))

    content = "\n".join([f"{i+1}. {ctx.page_content}" for i, ctx in enumerate(contexts)])

    messages = [
        ("system", "你是一个金融专家，请根据用户的问题和相关的知识库内容，给出专业、清晰的回答。"),
        ("human", f"问题：{question}\n\n"
                  f"参考内容：\n{content}\n\n"
                  f"请务必说明参考了以下文件：{', '.join(sources)}")
    ]

    response = llm.invoke(messages)
    answer = response.content
    kb.del_model()
    return answer


def main(query):
    os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
    # 配置路径
    DATA_DIR = "data/raw_data"
    INITIAL_DATA = os.path.join(DATA_DIR, "bank")
    UPDATES_DATA = os.path.join(DATA_DIR, "updates")

    # 创建知识库实例

    # 第一次运行：初始化知识库（只需一次）
    # kb.initialize_from_folder(INITIAL_DATA)

    # 后续运行：添加新文档（可选）
    #kb.add_file(os.path.join(UPDATES_DATA, "new_policy.pdf"))
    # kb.add_folder(UPDATES_DATA)

    # 任意次数提问
    result = ask(query)
    logger.info(f"回答:\n{result}")
    data = {
        "agent_type": "single_agent",
        "agent_response": result
    }
    yield data
    # ask("贷款有哪些类型？")
    # ask("最新的反洗钱政策是什么？")
    return result
if __name__ == "__main__":
    query="贷款有哪些类型？"
    main(query)
    