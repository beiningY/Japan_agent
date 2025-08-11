"""
支持用户管理知识库里的文件
支持功能
1. 添加文件（文件路径/知识库名称）
2. 删除文件（原文件路径/知识库名称/文件名称）
"""
# main.py
from rag_pipeline.auto_rag.knowledeg_base import KnowledgeBase
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
load_dotenv()
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AutoEmbedding")
logger.setLevel(logging.INFO)


def embedding(kb_name: str,file_path: str):
    os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
    kb = KnowledgeBase(
        persist_path="data/vector_data",
        collection_name=kb_name
    )
    kb.add_file(file_path)
    kb.del_model()
    return True

def delete(kb_name: str,file_path: str):
    kb = KnowledgeBase(
        persist_path="data/vector_data",
        collection_name=kb_name
    )
    kb.delete_file(file_path)   
    kb.del_model()
    return True

if __name__ == "__main__":
    kb_name = "default"
    file_path = "data/raw_data/default/test.txt"
    embedding(kb_name,file_path)
    #delete(kb_name,file_path)
    