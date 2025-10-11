"""
注意：此文件为旧版知识库问答实现，已被 DataAgent 的 MCP 工具方式替代。
建议使用 agents/data_agent.py 进行知识库检索和问答。
此文件仅保留用于向后兼容、测试和知识库管理功能。

支持用户管理新的知识库
支持功能
1. 创建知识库（知识库名称）
2. 删除知识库（知识库名称）
3. 链接默认agent进行对话（已废弃，建议使用DataAgent）
"""
from rag.lang_rag import LangRAG
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
load_dotenv()
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Default_KB_QA")
logger.setLevel(logging.INFO)

def create(kb_name: str):
    """
    新建知识库+首次上传文件夹
    首先必须确保原始文件夹里存在已经上传的文件
    """
    kb_path = os.path.join("data/raw_data",kb_name)
    if not os.path.exists(kb_path):
        os.makedirs(kb_path, exist_ok=True)
    kb = LangRAG(
        persist_path="data/vector_data",
        collection_name=kb_name
    )
    kb.initialize_from_folder(kb_path)
    logger.info(f"知识库{kb_name}创建完成")
    kb.release()
    return kb

def delete(kb_name: str):
    kb = LangRAG(
        persist_path="data/vector_data",
        collection_name=kb_name
    )
    kb_path = os.path.join("data/raw_data",kb_name)
    kb.delete_collection(kb_path)
    kb.release()
    logger.info(f"知识库{kb_name}删除完成")
    return True

def ask(question: str, k: int = 5, kb_name: str="all_data", model: str="gpt-4o-mini"):
    logger.info(f"\n问题: {question}")
    kb = LangRAG(
        persist_path = "data/vector_data",
        collection_name = kb_name
    )

    llm = ChatOpenAI(model=model, temperature=0.4, max_tokens=None)
    contexts = kb.retrieve(question, k=k)
    logger.info(f"检索到的是{contexts}")
    if not contexts:
        answer = "抱歉，知识库中未找到相关信息。"
        logger.info(f"回答: {answer}")
        return answer

    # 提取唯一源文件（兼容 Document 与 str）
    def _extract_source(item):
        try:
            if hasattr(item, "metadata") and isinstance(item.metadata, dict):
                return os.path.basename(item.metadata.get("source", "未知文件"))
        except Exception:
            pass
        return "日本陆上养殖知识库"

    sources = list(set([_extract_source(doc) for doc in contexts]))

    # 生成内容（兼容 Document 与 str）
    def _to_text(item):
        return item.page_content if hasattr(item, "page_content") else str(item)

    content = "\n".join([f"{i+1}. {_to_text(ctx)}" for i, ctx in enumerate(contexts)])

    messages = [
        ("system", "你是一个问答专家，请根据用户的问题和相关的知识库内容，给出专业、清晰的回答。"),
        ("human", f"问题：{question}\n\n"
                  f"参考内容：\n{content}\n\n"
                  f"请务必说明参考了以下文件：{', '.join(sources)}"
                  )
    ]

    response = llm.invoke(messages)
    answer = response.content
    logger.info(f"回答: {answer}")
    return answer


def get_kb_list():
    kb_list = LangRAG(
        persist_path = "data/vector_data",
        collection_name = "all_data"
    )
    return kb_list.get_kb_list()
def add_file(file_name: str, kb_name: str="all_data"):
    kb = LangRAG(
        persist_path = "data/vector_data",
        collection_name = kb_name
    )
    kb.add_file(file_name)
    return True
def deletefile(file_name: str, kb_name: str="all_data"):
    kb = LangRAG(
        persist_path = "data/vector_data",
        collection_name = kb_name
    )
    kb.delete_file(file_name)
    return True
if __name__ == "__main__":
    kb_name = "all_data"
    query="今天天气怎么样"
    # 创建知识库
    #kb = create_kb(kb_name)

    # 删除知识库
    #delete_kb(kb_name)

    # 提问
    result = ask(query,kb_name=kb_name)

    print(result)