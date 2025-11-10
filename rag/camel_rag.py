"""
CamelRAG - 基于CAMEL框架的手动向量化处理工具

此模块用于手动处理和初始化RAG数据，适用于：
- 批量处理结构化JSON数据
- 自定义chunking策略的数据向量化
- 初始化特定格式的知识库

注意：这是手动处理工具，不用于生产环境的自动化RAG服务
"""
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
from typing import Optional, List, Dict, Any, Callable

logger = logging.getLogger("Camel_RAG")
logger.setLevel(logging.INFO)

class CamelRAG:
    """基于CAMEL框架的RAG手动处理工具"""
    
    def __init__(
        self, 
        collection_name: str,
        embedding_model_path: str = "models/multilingual-e5-large",
        vector_storage_path: str = "data/vector_data"
    ):
        """初始化CamelRAG
        
        Args:
            collection_name: 向量集合名称
            embedding_model_path: Embedding模型路径
            vector_storage_path: 向量数据库存储路径
        """
        self.collection_name = collection_name
        self.embedding_model_path = embedding_model_path
        self.vector_storage_path = vector_storage_path
        
        # 初始化配置
        self.config = {
            "vector_top_k": 5,
            "similarity_threshold": 0.6,
            "chunk_size": 500,
            "chunk_overlap": 50
        }
        
        # 初始化组件
        self._initialize_components()

    def _initialize_components(self):
        """初始化CAMEL RAG组件"""
        try:
            logger.info(f"初始化CAMEL RAG组件: {self.collection_name}")
            
            # 初始化Tokenizer
            logger.info(f"加载Tokenizer: {self.embedding_model_path}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.embedding_model_path)
            
            # 初始化Embedding模型
            logger.info("初始化SentenceTransformerEncoder")
            self.embedding_instance = SentenceTransformerEncoder(
                model_name=self.embedding_model_path
            )
            
            # 初始化向量存储
            logger.info(f"初始化QdrantStorage: {self.collection_name}")
            self.vector_storage = QdrantStorage(
                collection_name=self.collection_name,
                path=self.vector_storage_path,
                embedding_dim=1024  # multilingual-e5-large的向量维度
            )
            
            # 初始化检索器
            logger.info("初始化VectorRetriever")
            self.vr = VectorRetriever(
                embedding_model=self.embedding_instance,
                storage=self.vector_storage
            )
            
            logger.info("✅ CAMEL RAG组件初始化完成")
            
        except Exception as e:
            logger.error(f"初始化CAMEL RAG组件失败: {e}")
            raise
    
    def embedding(
        self, 
        data_path: Optional[str] = None, 
        data: Optional[List[Dict]] = None, 
        chunk_type: Callable = chunk_data_by_title, 
        max_tokens: int = 500
    ):
        """向量化结构化数据
        
        Args:
            data_path: JSON数据文件路径（与data二选一）
            data: 结构化数据列表（与data_path二选一）
            chunk_type: chunking函数（chunk_data_by_title或chunk_data_for_log）
            max_tokens: 每个chunk的最大token数
        """
        if data is None and data_path is None:
            raise ValueError("必须提供data_path或data参数")
        
        # 加载数据
        if data is None:
            logger.info(f"从文件加载数据: {data_path}")
            with open(data_path, "r", encoding="utf-8") as f:
                structured_data = json.load(f)
        else:
            structured_data = data
        
        logger.info(f"数据项数量: {len(structured_data)}")
        
        # 分块处理
        logger.info(f"使用chunking函数: {chunk_type.__name__}, max_tokens={max_tokens}")
        chunks = chunk_type(
            structured_data,
            MAX_TOKENS=max_tokens,
            tokenizer=self.tokenizer,
        )
        
        logger.info(f"生成了 {len(chunks)} 个chunks")
        
        # 向量化并存储
        start_time = time.time()
        for i, chunk in enumerate(chunks):
            if (i + 1) % 10 == 0:
                logger.info(f"处理进度: {i+1}/{len(chunks)}")
            
            self.vr.process(
                content=chunk["content"],
                should_chunk=False,
                extra_info={
                    "id": chunk["chunk_id"], 
                    "title": chunk.get("title", ""), 
                    "type": chunk.get("type", "text")
                }
            )
        
        end_time = time.time()
        elapsed = end_time - start_time
        logger.info(f"✅ 向量化完成！共处理 {len(chunks)} 个chunks")
        logger.info(f"⏱️  耗时: {elapsed:.2f}秒 (平均 {elapsed/len(chunks):.3f}秒/chunk)")
        
        if data_path:
            logger.info(f"📄 数据源: {data_path}")

    def embedding_auto(self, data: List[str]):
        """自动向量化文本列表（无需chunking）
        
        Args:
            data: 文本列表
        """
        logger.info(f"开始自动向量化 {len(data)} 个文本")
        start_time = time.time()
        
        for i, chunk in enumerate(data):
            if (i + 1) % 10 == 0:
                logger.info(f"处理进度: {i+1}/{len(data)}")
            self.vr.process(content=chunk, should_chunk=False)

        end_time = time.time()
        elapsed = end_time - start_time
        logger.info(f"✅ 自动向量化完成！")
        logger.info(f"⏱️  耗时: {elapsed:.2f}秒")

    def rag_retrieve(self, query: str, topk: Optional[int] = None) -> List[str]:
        """检索相关文档
        
        Args:
            query: 查询文本
            topk: 返回top-k结果（None则使用配置中的默认值）
            
        Returns:
            检索结果列表
        """
        logger.info(f"🔍 RAG检索开始")
        logger.info(f"   查询: {query}")
        
        top_k = topk if topk is not None else self.config.get("vector_top_k", 5)
        similarity_threshold = self.config.get("similarity_threshold", 0.6)
        
        logger.info(f"   参数: top_k={top_k}, threshold={similarity_threshold}")
        
        results = self.vr.query(
            query=query, 
            top_k=top_k, 
            similarity_threshold=similarity_threshold
        )
        
        retrieved = []
        for i, info in enumerate(results):
            retrieved.append(f"{i+1}. {info['text']}\n\n")
        
        logger.info(f"✅ 检索完成，返回 {len(retrieved)} 个结果")
        
        # 只在DEBUG模式下打印详细结果
        if logger.level <= logging.DEBUG:
            logger.debug("检索结果详情:")
            for r in retrieved:
                logger.debug(r[:200] + "..." if len(r) > 200 else r)
        
        return retrieved
    
    def release(self):
        """释放资源"""
        logger.info("开始释放 RAG 占用的资源")
        
        # 清理引用
        self.vr = None 
        self.vector_storage = None
        self.embedding_instance = None
        self.tokenizer = None
        
        # 清理GPU缓存
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        # 强制垃圾回收
        gc.collect()
        
        logger.info("✅ 资源释放完成")

