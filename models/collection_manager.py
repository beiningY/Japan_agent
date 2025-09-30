"""
全局集合管理器
负责管理向量数据库集合的创建、缓存和访问
解决Qdrant并发访问问题，支持动态加载不同集合
"""
import logging
import threading
from typing import Optional, Dict, Any, Set
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from langchain_qdrant import QdrantVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from models.model_manager import model_manager

logger = logging.getLogger("CollectionManager")
logger.setLevel(logging.INFO)


class CollectionManager:
    """全局集合管理器，单例模式，线程安全"""
    
    _instance = None
    _initialized = False
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(CollectionManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self.vectorstores: Dict[str, QdrantVectorStore] = {}
                    self.available_collections: Set[str] = set()
                    self.vector_size = 1024
                    self.persist_path = "data/vector_data"
                    self._initialized = True
                    logger.info("全局集合管理器初始化完成")
    
    def initialize_collections(self, 
                              persist_path: str = "data/vector_data",
                              vector_size: int = 1024,
                              preload_collections: Optional[list] = None):
        """初始化集合管理器"""
        with self._lock:
            if hasattr(self, '_collections_initialized') and self._collections_initialized:
                logger.info("集合管理器已初始化，跳过重复初始化")
                return
                
            logger.info("开始初始化全局集合管理器...")
            
            self.persist_path = persist_path
            self.vector_size = vector_size
            
            # 获取全局模型管理器的客户端
            try:
                if model_manager.is_initialized():
                    self.client = model_manager.get_qdrant_client()
                    self.embedding_model = model_manager.get_embedding_model()
                    logger.info("使用全局模型管理器的客户端和embedding模型")
                else:
                    logger.warning("全局模型管理器未初始化，集合管理器将延迟初始化")
                    self.client = None
                    self.embedding_model = None
            except Exception as e:
                logger.error(f"获取全局模型管理器资源失败: {e}")
                self.client = None
                self.embedding_model = None
            
            # 预加载指定的集合
            if preload_collections:
                for collection_name in preload_collections:
                    try:
                        self._ensure_collection_exists(collection_name)
                        logger.info(f"预加载集合: {collection_name}")
                    except Exception as e:
                        logger.warning(f"预加载集合 {collection_name} 失败: {e}")
            
            self._collections_initialized = True
            logger.info("全局集合管理器初始化完成！")
    
    def _ensure_client_ready(self):
        """确保客户端和模型已准备就绪"""
        if self.client is None or self.embedding_model is None:
            if model_manager.is_initialized():
                self.client = model_manager.get_qdrant_client()
                self.embedding_model = model_manager.get_embedding_model()
                logger.info("延迟初始化：获取全局模型管理器资源")
            else:
                raise RuntimeError("全局模型管理器未初始化，无法获取客户端和embedding模型")
    
    def _ensure_collection_exists(self, collection_name: str) -> bool:
        """确保集合存在，如果不存在则创建"""
        self._ensure_client_ready()
        
        try:
            # 检查集合是否存在
            self.client.get_collection(collection_name)
            logger.info(f"集合已存在: {collection_name}")
            return True
        except Exception:
            # 集合不存在，创建新集合
            logger.info(f"创建新集合: {collection_name}")
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE)
            )
            self.available_collections.add(collection_name)
            logger.info(f"集合创建成功: {collection_name}")
            return True
    
    def get_vectorstore(self, collection_name: str) -> QdrantVectorStore:
        """获取向量存储实例，支持动态加载"""
        with self._lock:
            # 检查缓存
            if collection_name in self.vectorstores:
                logger.info(f"从缓存获取向量存储: {collection_name}")
                return self.vectorstores[collection_name]
            
            # 确保集合存在
            self._ensure_collection_exists(collection_name)
            
            # 创建新的向量存储实例
            logger.info(f"创建向量存储实例: {collection_name}")
            vectorstore = QdrantVectorStore(
                client=self.client,
                collection_name=collection_name,
                embedding=self.embedding_model,
            )
            
            # 缓存向量存储实例
            self.vectorstores[collection_name] = vectorstore
            logger.info(f"向量存储实例创建并缓存成功: {collection_name}")
            
            return vectorstore
    
    def create_collection(self, collection_name: str) -> bool:
        """创建新集合"""
        with self._lock:
            try:
                self._ensure_collection_exists(collection_name)
                logger.info(f"集合创建成功: {collection_name}")
                return True
            except Exception as e:
                logger.error(f"创建集合失败: {collection_name}, 错误: {e}")
                return False
    
    def delete_collection(self, collection_name: str) -> bool:
        """删除集合"""
        with self._lock:
            try:
                self._ensure_client_ready()
                
                # 删除集合
                self.client.delete_collection(collection_name)
                
                # 从缓存中移除
                if collection_name in self.vectorstores:
                    del self.vectorstores[collection_name]
                
                # 从可用集合列表中移除
                self.available_collections.discard(collection_name)
                
                logger.info(f"集合删除成功: {collection_name}")
                return True
            except Exception as e:
                logger.error(f"删除集合失败: {collection_name}, 错误: {e}")
                return False
    
    def list_collections(self) -> list:
        """列出所有可用集合"""
        with self._lock:
            try:
                self._ensure_client_ready()
                collections = self.client.get_collections()
                collection_names = [col.name for col in collections.collections]
                self.available_collections.update(collection_names)
                return collection_names
            except Exception as e:
                logger.error(f"获取集合列表失败: {e}")
                return list(self.available_collections)
    
    def get_collection_info(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """获取集合信息"""
        with self._lock:
            try:
                self._ensure_client_ready()
                collection_info = self.client.get_collection(collection_name)
                return {
                    "name": collection_name,
                    "vectors_count": collection_info.vectors_count,
                    "indexed_vectors_count": collection_info.indexed_vectors_count,
                    "points_count": collection_info.points_count,
                    "status": collection_info.status,
                    "optimizer_status": collection_info.optimizer_status,
                }
            except Exception as e:
                logger.error(f"获取集合信息失败: {collection_name}, 错误: {e}")
                return None
    
    def clear_cache(self, collection_name: Optional[str] = None):
        """清理缓存"""
        with self._lock:
            if collection_name:
                if collection_name in self.vectorstores:
                    del self.vectorstores[collection_name]
                    logger.info(f"清理集合缓存: {collection_name}")
            else:
                self.vectorstores.clear()
                logger.info("清理所有集合缓存")
    
    def is_initialized(self) -> bool:
        """检查集合管理器是否已初始化"""
        return hasattr(self, '_collections_initialized') and self._collections_initialized
    
    def release_resources(self):
        """释放资源"""
        with self._lock:
            logger.info("开始释放集合管理器资源...")
            
            # 清理向量存储缓存
            self.vectorstores.clear()
            
            # 清理集合列表
            self.available_collections.clear()
            
            # 重置初始化状态
            self._collections_initialized = False
            
            logger.info("集合管理器资源释放完成")


# 全局集合管理器实例
collection_manager = CollectionManager()
