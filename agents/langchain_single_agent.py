from agents.base import BaseAgent
from rag.lang_rag import LangRAG
from langchain_openai import ChatOpenAI
import os
import logging

logger = logging.getLogger("LangSingleAgent")
logger.setLevel(logging.INFO)

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



    def run(question: str, k: int = 5):
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
            ("system", "你是一个专家，请根据用户的问题和相关的知识库内容，给出专业、清晰的回答。"),
            ("human", f"问题：{question}\n\n"
                    f"参考内容：\n{content}\n\n"
                    f"请务必说明参考了以下文件：{', '.join(sources)}")
        ]

        response = llm.invoke(messages)
        answer = response.content
        kb.del_model()
        return answer

if __name__ == "__main__":
    query="贷款有哪些类型？"
    LangchainSingleAgent().run(query)
    