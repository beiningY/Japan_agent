"""
支持用户管理新的知识库
支持功能
1. 创建知识库（知识库名称）
2. 删除知识库（知识库名称）
3. 链接默认agent进行对话
"""
from rag_pipeline.lang_rag import LangRAG
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
load_dotenv()
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DefaultQA")
logger.setLevel(logging.INFO)

def create_kb(kb_name: str):
"""
创建知识库（知识库名称）
通过知识库名称
1.创建kb类 初始化向量库
2.链接原始文件文件夹（必须确保原始文件夹存在）
"""
    kb_path = os.path.join("data/raw_data",kb_name)
    kb = KnowledgeBase(
        persist_path="data/vector_data",
        collection_name=kb_name
    )
    kb.initialize_from_folder(kb_path)
    logger.info(f"知识库{kb_name}创建完成")
    kb.del_model()
    return kb

def ask(question: str, k: int = 5,kb_name: str,model: str="gpt-4o"):
    kb = KnowledgeBase(
        persist_path = "data/vector_data",
        collection_name = kb_name
    )

    llm = ChatOpenAI(model=model, temperature=0.4, max_tokens=None)
    logger.info(f"\n问题: {question}")
    contexts = kb.retrieve(question, k=k)
    logger.info(f"检索到的是{contexts}")
    if not contexts:
        answer = "抱歉，知识库中未找到相关信息。"
        logger.info(f"回答: {answer}")
        return answer

    # 提取唯一源文件
    #sources = list(set([
    #    os.path.basename(doc.metadata.get("source", "未知文件"))
    #    for doc in contexts
    #]))

    content = "\n".join([f"{i+1}. {ctx.page_content}" for i, ctx in enumerate(contexts)])

    messages = [
        ("system", "你是一个问答专家，请根据用户的问题和相关的知识库内容，给出专业、清晰的回答。"),
        ("human", f"问题：{question}\n\n"
                  f"参考内容：\n{content}\n\n"
                  #f"请务必说明参考了以下文件：{', '.join(sources)}"
                  )
    ]

    response = llm.invoke(messages)
    answer = response.content
    kb.del_model()
    return answer

if __name__ == "__main__":
    kb_name = "default"
    query="今天天气怎么样"
    # 创建知识库
    kb = create_kb(kb_name)
    # 提问
    result = ask(query,kb_name=kb_name)
    print(result)