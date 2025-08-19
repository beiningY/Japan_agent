"""
支持用户管理知识库里的文件
支持功能
1. 添加文件（文件路径/知识库名称）
2. 删除文件（原文件路径/知识库名称/文件名称）
"""
from rag.lang_rag import LangRAG
import os
from dotenv import load_dotenv
load_dotenv()
import logging

logger = logging.getLogger("AutoEmbedding")
logger.setLevel(logging.INFO)


def embedding(kb_name: str,file_path: str):
    os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
    kb = LangRAG(
        persist_path="data/vector_data",
        collection_name=kb_name
    )
    kb.add_file(file_path)
    kb.del_model()
    return True

def delete(kb_name: str,file_path: str):
    kb = LangRAG(
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
    