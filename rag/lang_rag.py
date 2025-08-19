# knowledge_base.py
import os
from typing import List
from langchain_core.documents import Document
from langchain_community.document_loaders import UnstructuredFileLoader, DirectoryLoader
from langchain.text_splitter import TokenTextSplitter
from langchain_qdrant import QdrantVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
import logging
import torch
import gc
import shutil
from uuid import uuid4

logger = logging.getLogger("Langchain_RAG")
logger.setLevel(logging.INFO)

class LangRAG:
    """
    知识库类可操作功能：
    - 初始化向量库
    - 增量添加文档
    - 检索相关片段
    """

    def __init__(
        self,
        persist_path: str = "vector_store",
        collection_name: str = "all_data",
        embedding_model_path: str = "models/multilingual-e5-large",
        vector_size: int = 1024,
        chunk_size: int = 200,
        chunk_overlap: int = 50,
    ):
        self.persist_path = persist_path
        self.collection_name = collection_name
        self.embedding_model_path = embedding_model_path
        self.vector_size = vector_size
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.client: QdrantClient = None
        self.embeddings = None
        self.vectorstore: QdrantVectorStore = None
        self._initialize()

    def _initialize(self):
        """初始化 embedding 模型和向量客户端"""
        logger.info(f"加载 Embedding 模型: {self.embedding_model_path}")
        self.embeddings = HuggingFaceEmbeddings(
            model_name=self.embedding_model_path,
            encode_kwargs={"batch_size": 8}
        )

        logger.info(f"连接向量数据库: {self.persist_path}")
        self.client = QdrantClient(path=self.persist_path)
        self._connect_or_create_collection()

    def _connect_or_create_collection(self):
        """创建或连接到 collection"""
        try:
            self.client.get_collection(self.collection_name)
            logger.info(f"已连接到集合: {self.collection_name}")
        except:
            logger.info(f"创建新集合: {self.collection_name}")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE)
            )

        self.vectorstore = QdrantVectorStore(
            client=self.client,
            collection_name=self.collection_name,
            embedding=self.embeddings,
        )

    def initialize_from_folder(self, folder_path: str):
        """首次构建知识库：从文件夹加载所有文档"""
        loader = DirectoryLoader(folder_path)

        docs = loader.load()
        logger.info(f"使用loader的docs{docs}")
        splitter = TokenTextSplitter(
            chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
        )
        chunks = splitter.split_documents(docs)
        logger.info(f"加载 {len(docs)} 个文档 → 切分为 {len(chunks)} 个文本块")
        logger.info(f"使用split的chunks{chunks}")
        self.vectorstore.add_documents(chunks)
        logger.info("知识库构建完成！")
        
    def delete_collection(self, raw_data_path: str):
        """删除知识库,包括删除向量知识库以及原文件夹"""
        self.client.delete_collection(self.collection_name)
        logger.info(f"知识库{self.collection_name}删除完成")
        # shutil.rmtree(f"{raw_data_path}/{self.collection_name}")
        logger.info(f"文件夹{raw_data_path}/{self.collection_name}删除完成")
        return True
    
    #=================可添加到知识库的文档类型 txt pdf xlsx docx csv ========
    # UnstructuredLoader支持txt html pad im

    def add_folder(self, folder_path: str):
        loader = DirectoryLoader(folder_path)

        docs = loader.load()
        logger.info(f"使用loader的docs{docs}")
        splitter = TokenTextSplitter(
            chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
        )
        chunks = splitter.split_documents(docs)
        logger.info(f"加载 {len(docs)} 个文档 → 切分为 {len(chunks)} 个文本块")
        logger.info(f"使用split的chunks{chunks}")
        self.vectorstore.add_documents(chunks)
        logger.info("知识库文件夹添加完成")

    def add_file(self, file_path: str):
        # 获取文件名
        file_name = os.path.basename(file_path)
        loader = UnstructuredFileLoader(file_path)
        docs = loader.load()
        logger.info(f"使用loader的docs{docs}")
        splitter = TokenTextSplitter(
            chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
        )
        id_chunks = []
        chunks = splitter.split_documents(docs)
        ids = [str(uuid4()) for _ in range(len(chunks))]
        for i,chunk in enumerate(chunks):
            id_chunks.append(Document(
                page_content=chunk.page_content,
                metadata={
                    "source": file_name,
                    "chunk_id": ids[i]
                }
            ))
        logger.info(f"加载 {len(docs)} 个文档 → 切分为 {len(chunks)} 个文本块")
        logger.info(f"使用split的chunks{id_chunks}")
        self.vectorstore.add_documents(id_chunks,ids=ids)
        logger.info("知识库文件添加完成")

    def delete_file(self, file_path: str):
        file_name = os.path.basename(file_path)
        # 先查出 file_id 对应的所有 chunk id
        results = self.vectorstore.similarity_search(
            query="",
            k=10000,
            filter={"source": file_name} 
        )

        chunk_ids_to_delete = [doc.metadata["chunk_id"] for doc in results]

        # 批量删除
        self.vectorstore.delete(ids=chunk_ids_to_delete)
        logger.info(f"文件{file_path}在向量知识库中删除完成")

    def retrieve(self, query: str, k: int = 5) -> List[Document]:
        """检索最相关的文档片段"""
        logger.info(f"检索中: '{query}' (top-{k})")
        query = f"query: {query}"
        # results = self.vectorstore.similarity_search_with_score(query, k=k)
        results = self.vectorstore.similarity_search(query, k=k)
        logger.info(f"检索到 {len(results)} 条相关片段")
        return results

    def del_model(self):
        """if hasattr(self, "embeddings") and self.embeddings is not None:
            try:
                # 如果 self.embeddings 是 HuggingFaceEmbeddings，真正的模型通常在 self.embeddings.client 或 self.embeddings.model
                self.embeddings.cpu()  
            except Exception as e:
                logger.warning(f"释放 CPU 时出错: {e}")"""

        # 清理引用
        self.embeddings = None
        self.vectorstore = None

        # 显存与内存回收
        torch.cuda.empty_cache()
        gc.collect()
        logger.info("释放显存")

