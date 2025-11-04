import json
import time
from embeddings import chunk_data_by_title, chunk_data_for_log
from camel.embeddings import SentenceTransformerEncoder
from camel.storages import QdrantStorage
from camel.retrievers import VectorRetriever
import os
from transformers import AutoTokenizer
import logging
import torch
import gc
from models.model_manager import ModelManager
logger = logging.getLogger("Camel_RAG")
logger.setLevel(logging.INFO)

class CamelRAG:
    def __init__(self, collection_name):
        self.collection_name = collection_name
        self.model_manager = ModelManager()
        self.is_model_init = self.model_manager.is_initialized()
        if not self.is_model_init:
            self.model_manager.initialize_models()
        self.vectorstore = self.model_manager.get_vectorstore(self.collection_name)

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
    
    def release(self):
        logger.info("开始释放 RAG 占用的资源")
        self.vr = None 
        self.vector_storage = None
        self.model_manager.del_model()

