import json
import time
from embeddings import chunk_data_by_title, chunk_data_for_log
from camel.embeddings import SentenceTransformerEncoder
from camel.storages import QdrantStorage
from camel.retrievers import VectorRetriever
import os
from transformers import AutoTokenizer
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("VectorRetriever")
logger.setLevel(logging.INFO)
class ModelManager:
    """避免重复加载模型"""
    _instance = None
    _embedding_model = None
    _tokenizer = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_embedding_model(self):
        if self._embedding_model is None:
            self._load_config()
            logger.info("正在加载embedding模型...")
            self._embedding_model = SentenceTransformerEncoder(model_name="models/multilingual-e5-large")
            logger.info("embedding模型加载完成")
        return self._embedding_model
    
    def get_tokenizer(self):
        if self._tokenizer is None:
            self._load_config()
            logger.info("正在加载tokenizer...")
            self._tokenizer = AutoTokenizer.from_pretrained("models/multilingual-e5-large")
            logger.info("tokenizer加载完成")
        return self._tokenizer
    
    def _load_config(self):
        if self._config is None:
            with open("utils/config.json", "r", encoding="utf-8") as f:
                self._config = json.load(f)
        return self._config
    
    def get_config(self):
        return self._load_config()

class RAG:
    def __init__(self, collection_name):
        self.collection_name = collection_name
        self.model_manager = ModelManager()
        self.config = self.model_manager.get_config()
        self.init_vector_store()
        os.environ["TOKENIZERS_PARALLELISM"] = "false"

    def init_vector_store(self):
        """初始化或者加载向量存储"""
        # 只在需要时加载embedding模型
        embedding_model = self.model_manager.get_embedding_model()
        self.vector_storage = QdrantStorage(
            vector_dim=embedding_model.get_output_dim(),
            path="data/knowledge_base",  
            collection_name=self.collection_name,
        )
        self.vr = VectorRetriever(embedding_model=embedding_model, storage=self.vector_storage)

    def embedding(self, data_path = None, data = None, chunk_type = chunk_data_by_title, max_tokens = 500):
        """向量化"""
        if data is None:
            with open(data_path, "r") as f:
                structured_data = json.load(f)
        else:
            structured_data = data
        
        # 只在需要时加载tokenizer
        tokenizer = self.model_manager.get_tokenizer()
        chunks = chunk_type(
            structured_data,
            MAX_TOKENS=max_tokens,
            tokenizer=tokenizer,
        )
        start_time = time.time()
        for chunk in chunks:
            self.vr.process(
                content=chunk["content"],
                should_chunk=False,
                extra_info={"id": chunk["chunk_id"], "title": chunk["title"], "type": chunk["type"]}
            )
        end_time = time.time()
        logger.info(f"{data_path}的embedding处理时间: {end_time - start_time:.4f} 秒")

    def embedding_auto(self, data):
        start_time = time.time()
        for chunk in data:
            self.vr.process(content=chunk, should_chunk=False)

        end_time = time.time()
        logger.info(f"embedding处理时间: {end_time - start_time:.4f} 秒")

    def rag_retrieve(self, query, topk=None):
        """进行检索"""
        logger.info(f"RAG检索开始，检索的query是：{query}")
        results = self.vr.query(
            query=query, 
            top_k=topk if topk is not None else self.config.get("vector_top_k", 5), 
            similarity_threshold=self.config.get("similarity_threshold", 0.6)
            )   
        retrieved = []
        for i, info in enumerate(results):
            retrieved.append(f"{i+1}. {info['text']}\n\n")  
        logger.info("RAG检索结果:")
        logger.info(retrieved)
        return retrieved          
    

    