# 全局Embedding模型管理器架构说明

## 概述

为了解决每次RAG操作都要重新加载embedding模型的性能问题，我们实现了一个全局embedding模型管理器，在API服务启动时一次性加载embedding模型，然后供整个应用程序共享使用。

**注意：本方案只管理本地部署的embedding模型，不管理远程API的LLM模型（如OpenAI API）。**

## 架构改进

### 之前的问题
- 每次创建 `LangRAG` 实例时都要加载 embedding 模型
- 导致大量重复的embedding模型加载，消耗内存和时间
- 特别是在高并发场景下，重复加载会严重影响性能

### 现在的解决方案
- **全局Embedding模型管理器**：单例模式，确保embedding模型只加载一次
- **启动时初始化**：API服务启动时后台线程初始化embedding模型
- **共享访问**：所有RAG组件通过全局管理器访问预加载的embedding模型
- **LLM保持不变**：问答模型（ChatOpenAI等）保持原有的使用方式
- **向后兼容**：如果全局管理器未初始化，自动降级到传统模式

## 核心文件

### 1. `models/model_manager.py` - 全局Embedding模型管理器
- **ModelManager类**：单例模式的全局embedding模型管理器
- **功能**：
  - 初始化和管理 Embedding 模型
  - 管理 Qdrant 客户端和向量存储
  - 提供统一的embedding模型访问接口

### 2. `api/main.py` - API启动入口
- **改进**：添加了后台embedding模型初始化线程
- **initialize_models()函数**：负责在启动时初始化全局embedding模型管理器

### 3. `rag/lang_rag.py` - RAG类重构
- **改进**：
  - 优先使用全局模型管理器中的embedding模型
  - 如果全局管理器未初始化，降级到传统模式
  - 简化 `release()` 方法，不释放全局共享的embedding模型
  - LLM相关代码保持不变

### 4. LLM使用保持不变
- 所有使用 `ChatOpenAI` 的地方保持原有方式
- `agents/langchain_single_agent.py`
- `agents/sql_agent.py` 
- `run_qa/lang_kb_qa.py`

这些文件中的LLM创建方式没有改变，只有embedding相关的部分受益于全局管理器。

## 使用方法

### 启动API服务
```bash
python api/main.py
```

API服务会自动在后台初始化模型。

### 手动测试模型初始化
```bash
python init_models.py
```

### 在代码中使用
```python
from models.model_manager import model_manager

# 获取 embedding 模型
embedding_model = model_manager.get_embedding_model()

# 获取向量存储
vectorstore = model_manager.get_vectorstore("collection_name")

# LLM模型仍然使用原有方式
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.4)
```

## 性能优势

1. **启动时间**：Embedding模型只在服务启动时加载一次
2. **内存效率**：避免重复加载相同的embedding模型
3. **响应速度**：RAG操作无需等待embedding模型加载
4. **资源管理**：统一的embedding模型生命周期管理
5. **LLM灵活性**：问答模型保持原有的灵活创建方式，支持不同参数配置

## 向后兼容性

代码设计为向后兼容：
- 如果全局模型管理器可用，使用预加载的embedding模型
- 如果全局模型管理器不可用，自动降级到传统模式
- LLM相关功能完全不受影响
- 不会破坏现有的功能

## 配置参数

默认配置（在 `api/main.py` 和 `init_models.py` 中）：
- **embedding_model_path**: `"models/multilingual-e5-large"`
- **vector_persist_path**: `"data/vector_data"`
- **vector_size**: `1024`

可以根据需要在这些文件中修改配置。

## 日志监控

通过日志可以监控embedding模型管理器的状态：
- Embedding模型初始化成功/失败
- 使用全局embedding模型管理器还是传统模式
- 各个RAG组件的embedding模型获取情况

查看日志示例：
```
INFO - EmbeddingModelManager - 开始初始化全局Embedding模型管理器...
INFO - EmbeddingModelManager - 加载 Embedding 模型: models/multilingual-e5-large
INFO - EmbeddingModelManager - Embedding 模型加载成功
INFO - EmbeddingModelManager - 全局Embedding模型管理器初始化完成！
INFO - Langchain_RAG - 从全局模型管理器获取模型成功
```
