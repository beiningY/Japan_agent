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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AutoKnowledgeBaseAPI")
logger.setLevel(logging.INFO)

class KnowledgeBase:
    """
    知识库类可操作功能：
    - 初始化向量库
    - 增量添加文档
    - 检索相关片段
    """

    def __init__(
        self,
        persist_path: str = "vector_store",
        collection_name: str = "finance_kb",
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
            encode_kwargs={"batch_size": 16}
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

    def _load_and_split(self, docs: List[Document]) -> List[Document]:
        """切分文档并添加前缀"""
        splitter = TokenTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        chunks = splitter.split_documents(docs)
        for chunk in chunks:
            chunk.page_content = f"passage: {chunk.page_content}"
        return chunks

    def initialize_from_folder(self, folder_path: str):
        """首次构建知识库：从文件夹加载所有文档"""
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"文件夹不存在: {folder_path}")

        logger.info(f"初始化知识库,加载文档: {folder_path}")
        loader = DirectoryLoader(
            folder_path,
            loader_cls=UnstructuredFileLoader,
            use_multithreading=True,
            recursive=True,
            max_concurrency=2,  # 控制线程数
            show_progress=True,  
        )
        docs = loader.load()
        chunks = self._load_and_split(docs)

        logger.info(f"加载 {len(docs)} 个文档 → 切分为 {len(chunks)} 个文本块")
        self.vectorstore.add_documents(chunks)
        logger.info("知识库构建完成！")

    def add_file(self, file_path: str):
        """添加单个新文件"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        logger.info(f"添加新文件: {file_path}")
        loader = UnstructuredFileLoader(file_path)
        docs = loader.load()
        chunks = self._load_and_split(docs)
        self.vectorstore.add_documents(chunks)
        logger.info(f"文件 '{os.path.basename(file_path)}' 已添加")

    def add_folder(self, folder_path: str):
        """添加整个文件夹的文档"""
        if not os.path.exists(folder_path):
            logger.info(f"[!] 文件夹不存在，跳过: {folder_path}")
            return

        logger.info(f"添加新文件夹: {folder_path}")
        loader = DirectoryLoader(
            folder_path,
            loader_cls=UnstructuredFileLoader,
            use_multithreading=True,
            recursive=True
        )
        docs = loader.load()
        chunks = self._load_and_split(docs)
        self.vectorstore.add_documents(chunks)
        logger.info(f"文件夹 '{os.path.basename(folder_path)}' 中所有文档已添加")

    def retrieve(self, query: str, k: int = 5) -> List[Document]:
        """检索最相关的文档片段"""
        logger.info(f"检索中: '{query}' (top-{k})")
        query = f"query: {query}"
        results = self.vectorstore.similarity_search(query, k=k)
        logger.info(f"检索到 {len(results)} 条相关片段")
        return results

    def del_model(self):
        """if hasattr(self, "embeddings") and self.embeddings is not None:
            try:
                # 如果 self.embeddings 是 HuggingFaceEmbeddings，真正的模型通常在 self.embeddings.client 或 self.embeddings.model
                self.embeddings.cpu()  # ← 请根据具体结构调整
            except Exception as e:
                logger.warning(f"释放 CPU 时出错: {e}")"""

        # 清理引用
        self.embeddings = None
        self.vectorstore = None

        # 显存与内存回收
        torch.cuda.empty_cache()
        gc.collect()
        logger.info("释放显存")

