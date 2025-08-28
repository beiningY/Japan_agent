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
from langchain_community.chat_models import ChatOpenAI
from typing import List
import logging
from openai import OpenAI
import json
import dotenv
from models.model_manager import model_manager
dotenv.load_dotenv()

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
        """使用全局模型管理器初始化模型和向量客户端"""
        logger.info("使用全局模型管理器获取预加载的模型...")
        
        # 详细检查全局模型管理器状态
        logger.info(f"模型管理器状态检查: {id(model_manager)}")
        is_init = model_manager.is_initialized()
        logger.info(f"全局模型管理器初始化状态: {is_init}")
        
        if not is_init:
            logger.warning("全局模型管理器未初始化，使用传统方式加载模型")
            # 降级到传统方式
            logger.info(f"加载 Embedding 模型: {self.embedding_model_path}")
            self.embeddings = HuggingFaceEmbeddings(
                model_name=self.embedding_model_path,
                encode_kwargs={"batch_size": 8}
            )
            logger.info(f"连接向量数据库: {self.persist_path}")
            self.client = QdrantClient(path=self.persist_path)
        else:
            # 使用全局模型管理器
            try:
                self.embeddings = model_manager.get_embedding_model()
                self.client = model_manager.get_qdrant_client()
                logger.info("从全局模型管理器获取模型成功")
            except Exception as e:
                logger.error(f"从全局模型管理器获取模型失败: {e}")
                logger.warning("降级到传统方式加载模型")
                self.embeddings = HuggingFaceEmbeddings(
                    model_name=self.embedding_model_path,
                    encode_kwargs={"batch_size": 8}
                )
                self.client = QdrantClient(path=self.persist_path)
        
        self._connect_or_create_collection()

    def _connect_or_create_collection(self):
        """创建或连接到 collection"""
        # 如果使用全局模型管理器，直接获取 vectorstore
        if model_manager.is_initialized():
            self.vectorstore = model_manager.get_vectorstore(self.collection_name)
            logger.info(f"从全局模型管理器获取向量存储: {self.collection_name}")
        else:
            # 传统方式创建 vectorstore
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

    def rerank(self, query: str, results: List[Document], k: int = 5) -> List[Document]:
        """
        使用 LangChain LLM 对检索结果进行 cross-encoder 重排序
        Args:
            query: 用户查询
            results: 检索到的 Document 列表
            k: 返回 cross-encoder的top-k 排序结果
            
        Returns:
            List[Document]: 按相关性排序后的文档列表
        """
        if not results:
            return []

        # 构建候选文本，同时保存索引映射
        candidate_texts = [doc.page_content for doc in results]
        doc_index_map = {doc.page_content: i for i, doc in enumerate(results)}

        # 构建 prompt，让 LLM 对候选文本打分
        prompt = f"""
    你是一个搜索重排序器。给定一个查询和若干候选文档，请为每个候选文档给出 0~10 的相关性分数，分数越高表示越相关。如果与查询毫无关系请直接删除，不需要返回在json格式里
    查询: {query}

    候选文档:
    """
        for i, text in enumerate(candidate_texts, 1):
            prompt += f"{i}. {text}\n"

        prompt += """
    请输出 JSON 格式：
    [
    {"context": "实际的文档内容", "score": 6},
    {"context": "实际的文档内容", "score": 7},
    ...
    ]
    注意：context字段必须是原文档的完整内容，不要截断或修改。
    只输出 JSON格式，不要额外文字。
    """

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        schema = {
            "name": "rerank_response",
            "schema": {
                "type": "object",
                "properties": {
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "context": {"type": "string"},
                                "score": {"type": "integer"}
                            },
                            "required": ["context", "score"]
                        }
                    }
                },
                "required": ["results"]
            }
        }

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={
                "type": "json_schema",
                "json_schema": schema
            },
            messages=[
                {"role": "system", "content": "你是一个搜索重排序器。"},
                {"role": "user", "content": prompt},
            ],
        )

        scores_list = json.loads(response.choices[0].message.content)["results"]

        logger.info(f"重排序结果: {scores_list}")
        scored_docs = sorted(scores_list, key=lambda x: x["score"], reverse=True)

        # 根据重排序结果重新组织Document对象
        reranked_documents = []
        for scored_item in scored_docs:
            context_text = scored_item["context"]
            # 在原始文档中找到对应的Document对象
            for doc in results:
                if doc.page_content == context_text or context_text in doc.page_content:
                    reranked_documents.append(doc)
                    break
        
        return reranked_documents[:k]


    def retrieve(self, query: str, k: int = 5) -> List[Document]:
        """检索最相关的文档片段"""
        logger.info(f"检索中: '{query}' (top-{k})")
        query = f"query: {query}"
        # results = self.vectorstore.similarity_search_with_score(query, k=k)
        retrieve_results = self.vectorstore.similarity_search(query, k=k)
        logger.info(f"检索到相关片段:{retrieve_results}")
        #rerank_results = self.rerank(query, retrieve_results, k)
        #logger.info(f"重排序后相关片段 {rerank_results} ")
        return retrieve_results


    def release(self):
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

