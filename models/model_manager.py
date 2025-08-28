"""
全局Embedding模型管理器
负责在API服务启动时加载embedding模型，并提供全局访问接口
只管理本地部署的embedding模型，不管理远程API的LLM模型
"""
import logging
import torch
import gc
from typing import Optional, Dict, Any
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from langchain_qdrant import QdrantVectorStore
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("EmbeddingModelManager")
logger.setLevel(logging.INFO)


class ModelManager:
    """全局Embedding模型管理器，单例模式"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.embedding_model = None
            self.qdrant_clients: Dict[str, QdrantClient] = {}
            self.vectorstores: Dict[str, QdrantVectorStore] = {}
            self.vector_size = 1024
            self._initialized = True
    
    def initialize_models(self, 
                         embedding_model_path: str = "models/multilingual-e5-large",
                         vector_persist_path: str = "data/vector_data",
                         vector_size: int = 1024,
                         device: str = "auto"):
        """初始化embedding模型和向量数据库连接"""
        
        # 检查是否已经初始化过了
        if self.is_initialized():
            logger.info("全局Embedding模型管理器已初始化，跳过重复初始化")
            return
            
        logger.info("开始初始化全局Embedding模型管理器...")
        
        # 清理可能存在的显存占用
        self._clear_gpu_memory()
        
        # 初始化 Embedding 模型
        self._initialize_embedding_model(embedding_model_path, device)
        
        # 初始化向量数据库连接
        try:
            self._initialize_vector_clients(vector_persist_path, vector_size)
        except Exception as e:
            logger.error(f"向量数据库初始化失败，但Embedding模型已加载: {e}")
            # 创建一个临时的客户端标记，确保is_initialized返回True
            self.qdrant_clients["default"] = None
            self.vector_size = vector_size
            logger.warning("向量数据库连接失败，将在使用时延迟初始化")
        
        logger.info("全局Embedding模型管理器初始化完成！")
    
    def _clear_gpu_memory(self):
        """清理GPU显存"""
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                gc.collect()
                logger.info("已清理GPU显存缓存")
        except Exception as e:
            logger.warning(f"清理GPU显存时出错: {e}")
    
    def _initialize_embedding_model(self, model_path: str, device: str = "auto"):
        """初始化 Embedding 模型"""
        try:
            logger.info(f"加载 Embedding 模型: {model_path}")
            
            # 设备选择逻辑
            model_kwargs = {}
            if device == "cpu":
                model_kwargs["device"] = "cpu"
                logger.info("强制使用CPU运行embedding模型")
            elif device == "cuda":
                model_kwargs["device"] = "cuda"
                logger.info("强制使用GPU运行embedding模型")
            else:  # auto
                # 自动检测：优先GPU，显存不足时使用CPU
                import torch
                if torch.cuda.is_available():
                    try:
                        # 检查显存是否足够
                        model_kwargs["device"] = "cuda"
                        logger.info("检测到GPU，尝试使用GPU运行embedding模型")
                    except:
                        model_kwargs["device"] = "cpu"
                        logger.info("GPU显存不足，改用CPU运行embedding模型")
                else:
                    model_kwargs["device"] = "cpu"
                    logger.info("未检测到GPU，使用CPU运行embedding模型")
            
            self.embedding_model = HuggingFaceEmbeddings(
                model_name=model_path,
                model_kwargs=model_kwargs,
                encode_kwargs={"batch_size": 4}  # 减小batch_size以节省显存
            )
            logger.info(f"Embedding 模型加载成功，运行设备: {model_kwargs.get('device', 'auto')}")
        except Exception as e:
            logger.error(f"Embedding 模型加载失败: {e}")
            # 如果是显存不足，尝试使用CPU
            if "CUDA" in str(e) and "out of memory" in str(e):
                logger.warning("显存不足，尝试使用CPU加载embedding模型")
                try:
                    self.embedding_model = HuggingFaceEmbeddings(
                        model_name=model_path,
                        model_kwargs={"device": "cpu"},
                        encode_kwargs={"batch_size": 4}
                    )
                    logger.info("Embedding 模型已成功加载到CPU")
                except Exception as cpu_e:
                    logger.error(f"CPU加载也失败: {cpu_e}")
                    raise
            else:
                raise
    
    def _initialize_vector_clients(self, persist_path: str, vector_size: int):
        """初始化向量数据库客户端"""
        try:
            logger.info(f"初始化向量数据库连接: {persist_path}")
            
            # 检查是否已有客户端实例
            if "default" in self.qdrant_clients:
                logger.info("向量数据库客户端已存在，跳过重复初始化")
                return
                
            # 创建客户端
            default_client = QdrantClient(path=persist_path)
            self.qdrant_clients["default"] = default_client
            self.vector_size = vector_size
            logger.info("向量数据库连接初始化成功")
                    
        except Exception as e:
            logger.error(f"向量数据库连接失败: {e}")
            raise
    
    def get_embedding_model(self) -> HuggingFaceEmbeddings:
        """获取 Embedding 模型"""
        if self.embedding_model is None:
            raise RuntimeError("Embedding 模型未初始化，请先调用 initialize_models()")
        return self.embedding_model
    

    
    def get_vectorstore(self, collection_name: str = "all_data") -> QdrantVectorStore:
        """获取向量存储实例"""
        if collection_name in self.vectorstores:
            return self.vectorstores[collection_name]
        
        # 创建新的向量存储实例
        client = self.qdrant_clients.get("default")
        if client is None:
            raise RuntimeError("向量数据库客户端未初始化")
        
        if self.embedding_model is None:
            raise RuntimeError("Embedding 模型未初始化")
        
        # 检查集合是否存在，不存在则创建
        try:
            client.get_collection(collection_name)
            logger.info(f"连接到现有集合: {collection_name}")
        except:
            logger.info(f"创建新集合: {collection_name}")
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE)
            )
        
        # 创建向量存储实例
        vectorstore = QdrantVectorStore(
            client=client,
            collection_name=collection_name,
            embedding=self.embedding_model,
        )
        
        # 缓存向量存储实例
        self.vectorstores[collection_name] = vectorstore
        logger.info(f"向量存储实例创建成功: {collection_name}")
        
        return vectorstore
    
    def get_qdrant_client(self) -> QdrantClient:
        """获取 Qdrant 客户端"""
        client = self.qdrant_clients.get("default")
        if client is None:
            raise RuntimeError("Qdrant 客户端未初始化，请先调用 initialize_models()")
        return client
    
    def release_models(self):
        """释放模型资源"""
        logger.info("开始释放模型资源...")
        
        # 清理 embedding 模型
        self.embedding_model = None
        
        # 清理向量存储实例
        self.vectorstores.clear()
        
        # 清理 Qdrant 客户端
        for client in self.qdrant_clients.values():
            try:
                client.close()
            except:
                pass
        self.qdrant_clients.clear()
        
        # 清理显存和内存
        torch.cuda.empty_cache()
        gc.collect()
        
        logger.info("模型资源释放完成")
    
    def is_initialized(self) -> bool:
        """检查embedding模型是否已初始化"""
        # 只要embedding模型加载成功就认为已初始化，向量数据库可以延迟初始化
        return self.embedding_model is not None


# 全局模型管理器实例
model_manager = ModelManager()
