# 🦐 Camel Agent - 智能多源数据分析系统

> **基于 MCP 工具调度 + RAG 检索 + ReAct 智能体的南美白对虾养殖知识问答与数据分析系统**

---

## 📚 目录（Table of Contents）
- [项目简介](#-项目简介)
- [功能特性](#-功能特性)
- [系统架构](#-系统架构)
- [目录结构](#-目录结构)
- [快速开始](#-快速开始)
- [环境配置](#-环境配置)
- [核心模块说明](#-核心模块说明)
- [API 文档](#-api-文档)
- [技术栈](#-技术栈)
- [测试与验证](#-测试与验证)
- [部署指南](#-部署指南)
- [常见问题](#-常见问题)
- [版本记录](#-版本记录)
- [许可证](#-许可证)

---

## 📝 项目简介

**Camel Agent** 是一款基于 MCP (Model Context Protocol) 工具调度架构的智能数据分析系统，专为南美白对虾养殖场景设计，提供：

- 📖 **知识库检索**：从养殖手册、操作日志中快速检索相关知识
- 🗄️ **数据库查询**：自动生成 SQL 并查询养殖数据库
- 🤖 **智能推理**：基于 ReAct 架构的自主决策与工具调用
- 📊 **多源融合**：统一调度知识库、数据库、网络搜索等多种数据源
- ⚡ **流式响应**：Server-Sent Events (SSE) 实现实时反馈

> 本项目适用于 **农业 AI 助手、知识检索、数据分析、决策支持** 等场景，支持本地化部署。

---

## ✨ 功能特性

### 🔎 智能检索与多源数据获取
- **向量检索**：基于 Qdrant + multilingual-e5-large embedding 的语义检索
- **数据库工具**：自动列表、查询表结构、执行 SQL 查询
- **联网搜索**：通过 Tavily API 获取最新养殖技术信息

### 🧠 自主智能体
- **ReAct 架构**：思考-行动-观察循环，自主决策工具调用
- **MCP 工具调度**：统一的工具注册、权限管理、执行框架
- **DataAgent**：专门针对知识库 + 数据库的数据分析智能体
- **防止过度检索**：智能判断信息充足性，避免重复调用

### 📡 高可用 API 服务
- **Flask REST API**：稳定的 RESTful 接口
- **SSE 流式输出**：实时推送智能体思考过程和工具调用状态
- **队列化 RAG**：FIFO 队列管理，避免并发冲突，确保稳定性
- **全局模型管理**：单例模式管理 Embedding 模型，避免重复加载

### 📂 知识库管理
- **多集合管理**：支持 japan_shrimp、bank、all_data 等多个知识库
- **文档增删改查**：动态添加/删除文档和文件夹
- **多格式支持**：PDF、DOCX、TXT、CSV、HTML 等
- **自动分块**：TokenTextSplitter 自动切分长文档

---

## 🏗 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        客户端 / 前端                          │
│                    (HTTP / SSE Streaming)                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    Flask API Server                          │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Routes:  /api/kb/*  |  /api/qa/stream                │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   Agent Orchestrator                         │
│  ┌──────────────────┐          ┌────────────────────────┐  │
│  │   DataAgent      │◄────────►│ ToolOrchestrator       │  │
│  │  (ReAct Loop)    │          │  (MCP Tool Registry)   │  │
│  └──────────────────┘          └────────────────────────┘  │
└──────────────┬──────────────────────────┬──────────────────┘
               │                          │
       ┌───────▼───────┐          ┌──────▼─────────────┐
       │  LLM Service  │          │  Tool Execution    │
       │  (GPT-4o-mini)│          │   ┌─────────────┐  │
       └───────────────┘          │   │ KB Tools    │  │
                                  │   │ DB Tools    │  │
                                  │   │ Web Search  │  │
                                  │   └─────────────┘  │
                                  └──────┬────────────┘
                                         │
              ┌──────────────────────────┼──────────────────────┐
              │                          │                       │
    ┌─────────▼──────────┐   ┌──────────▼────────┐   ┌────────▼──────┐
    │  Qdrant Vector DB  │   │   MySQL Database  │   │  Tavily API   │
    │ (multilingual-e5)  │   │ (Aliyun RDS)      │   │ (Web Search)  │
    └────────────────────┘   └───────────────────┘   └───────────────┘
```

**架构说明：**
1. **API 层**：Flask 提供 RESTful 接口和 SSE 流式端点
2. **智能体层**：DataAgent 基于 ReAct 架构自主决策，循环调用工具
3. **工具调度层**：ToolOrchestrator 通过 MCP 协议管理工具注册、权限、执行
4. **数据层**：Qdrant 向量数据库、MySQL 关系数据库、Tavily 联网搜索
5. **LLM 层**：GPT-4o-mini 用于智能推理、工具选择、自然语言生成

---

## 📁 目录结构

```
Camel_agent/
├── agent_orchestrator.py      # Agent 编排器，负责任务调度和流程控制
│
├── agents/                     # 智能体模块
│   ├── core_base.py            # 智能体基类
│   ├── core_schema.py          # 数据结构定义 (AgentState, Message)
│   ├── react_agent.py          # ReAct 智能体基类实现
│   ├── mcp_toolcall_agent.py   # MCP 工具调用智能体
│   ├── data_agent.py           # 数据分析智能体 (KB + DB)
│   └── sql_agent.py            # SQL 查询专用智能体
│
├── api/                        # API 服务层
│   ├── main.py                 # Flask 应用入口
│   └── routes/                 # 路由模块
│       ├── knowledge_base.py   # 知识库管理接口
│       └── qa_sse.py           # 问答 SSE 流式接口
│
├── rag/                        # RAG 检索模块
│   ├── lang_rag.py             # LangChain + Qdrant RAG 实现
│   └── camel_rag.py            # CAMEL 框架 RAG 实现
│
├── ToolOrchestrator/           # MCP 工具调度系统
│   ├── core/                   # 核心模块
│   │   ├── config.py           # 工具配置管理
│   │   ├── registry.py         # 工具注册器
│   │   └── security.py         # 权限验证
│   ├── tools/                  # 工具实现
│   │   ├── kb_tools.py         # 知识库工具
│   │   ├── db_tools.py         # 数据库工具
│   │   ├── web_search_tools.py # 联网搜索工具
│   │   ├── config.json         # 工具配置文件
│   │   └── permissions.json    # 工具权限配置
│   ├── client/                 # 工具客户端
│   │   └── client.py           # 工具调用客户端
│   └── services/               # 工具服务
│       ├── kb_server.py        # 知识库服务
│       └── db_server.py        # 数据库服务
│
├── models/                     # 模型管理
│   ├── model_manager.py        # 全局 Embedding 模型管理器
│   ├── collection_manager.py   # 向量集合管理器
│   ├── init_models.py          # 模型初始化脚本
│   └── multilingual-e5-large/  # 本地 Embedding 模型
│
├── embeddings/                 # 向量化模块
│   ├── pre_embedding.py        # 手动向量化脚本
│   ├── auto_embedding.py       # 自动向量化
│   └── japan_book_chunking.py  # 养殖手册分块处理
│
├── dataprocess/                # 数据处理模块
│   ├── clean_book_zh.py        # 中文书籍清洗
│   ├── clean_log.py            # 日志清洗
│   ├── load_log.py             # 日志加载
│   └── csv_sql.py              # CSV 转 SQL
│
├── queue_rag/                  # RAG 队列管理
│   └── queue_server.py         # FIFO 队列服务
│
├── flow/                       # 工作流模块
│   ├── base.py                 # 流程基类
│   ├── factory.py              # 流程工厂
│   ├── planning.py             # 规划流程
│   └── planning_tool.py        # 规划工具
│
├── config/                     # 配置文件
│   ├── default_config.json     # 默认参数配置
│   ├── agent_config.json       # Agent 配置
│   └── config_description.json # 配置说明文档
│
├── data/                       # 数据目录
│   ├── raw_data/               # 原始数据
│   │   ├── japan_shrimp/       # 日本养殖手册
│   │   └── bank/               # 银行相关数据
│   ├── json_data/              # JSON 格式数据
│   └── vector_data/            # 向量数据库存储
│       └── collection/         # 各知识库集合
│           ├── japan_shrimp/
│           ├── bank/
│           ├── all_data/
│           └── knowledge_base/
│
├── benchmark/                  # 基准测试
│   ├── eval_stream_qa.py       # 问答评估脚本
│   └── 南美白对虾问题集.json   # 测试问题集
│
├── tests/                      # 测试模块
│   ├── test_sql_agent.py       # SQL Agent 测试
│   ├── test_kb.py              # 知识库测试
│   ├── test_web_search.py      # 网络搜索测试
│   └── test_server_sse.py      # SSE 服务测试
│
├── interface/                  # 前端界面
│   └── japan_interface.py      # Gradio 界面（可选）
│
├── utils/                      # 工具函数
│   ├── logger.py               # 日志管理
│   └── global_tool_manager.py  # 全局工具管理器
│
├── logs/                       # 日志目录
│   └── api.log                 # API 日志
│
├── run_qa/                     # 运行脚本
│   └── lang_kb_qa.py           # 知识库问答脚本
│
├── run_data_agent.py           # DataAgent 运行脚本
├── run_flow.py                 # 工作流运行脚本
└── README.md                   # 项目说明文档
```

---

## 🚀 快速开始

### 1. 克隆项目
```bash
git clone <your-repository-url>
cd Camel_agent
```

### 2. 创建虚拟环境并安装依赖
```bash
conda create -n camel_agent python=3.10
conda activate camel_agent
pip install -r requirements.txt
```

### 3. 配置环境变量

创建 `.env` 文件并添加必要的 API Keys：

```env
# OpenAI API (用于 LLM 推理)
OPENAI_API_KEY=your_openai_api_key_here

# 或者使用 GPT_API_KEY（备用）
GPT_API_KEY=your_gpt_api_key_here

# Tavily API (联网搜索功能)
TAVILY_API_KEY=your_tavily_api_key_here

# MySQL 数据库配置（如需修改）
DB_HOST=your_mysql_host
DB_USER=your_mysql_user
DB_PASSWORD=your_mysql_password
DB_NAME=cognitive
```

### 4. 下载 Embedding 模型

```bash
# 方式一：使用项目脚本下载
python download/download_model.py

# 方式二：手动下载 multilingual-e5-large 模型
# 下载到 models/multilingual-e5-large/ 目录
```

### 5. 初始化向量数据库（可选）

```bash
# 如果需要从头构建知识库
python embeddings/pre_embedding.py
```

### 6. 启动 API 服务

```bash
python api/main.py
```

服务启动后：
- API 服务运行在 `http://localhost:5001`
- 可以通过 `/api/qa/stream` 进行流式问答
- 通过 `/api/kb/*` 管理知识库

---

## 💻 环境配置

### 系统要求
- **Python**: >= 3.10
- **CUDA**: >= 11.8 (推荐 GPU，CPU 也可运行)
- **内存**: >= 16GB RAM
- **存储**: >= 10GB (用于模型和向量数据库)

### 主要依赖

```txt
# Web 框架
flask==3.0.0

# AI 框架
langchain==0.3.0
langchain-community==0.3.0
langchain-core==0.3.0
langchain-huggingface==0.1.0
langchain-qdrant==0.2.0

# 向量数据库
qdrant-client==1.11.0
faiss-cpu==1.8.0  # 可选

# Embedding 模型
sentence-transformers==3.0.0
transformers==4.44.0

# LLM
openai==1.40.0

# 联网搜索
tavily-python==0.5.0

# 数据库
aiomysql==0.2.0
pymysql==1.1.0

# 数据处理
pandas==2.2.0
numpy==1.26.0

# 工具
python-dotenv==1.0.0
pydantic==2.8.0
```

完整依赖请参考项目根目录的 `requirements.txt`（如有）。

---

## 🔍 核心模块说明

### 1. Agent Orchestrator (`agent_orchestrator.py`)
- **功能**：任务编排和流程控制
- **输入**：用户查询 + 配置参数
- **输出**：流式响应生成器（包含思考、工具调用、最终答案）
- **支持模式**：`single` (DataAgent)、`auto` (自动选择)

### 2. DataAgent (`agents/data_agent.py`)
- **功能**：专门针对知识库和数据库的智能体
- **特点**：
  - 继承 MCPToolCallAgent，使用 ReAct 架构
  - 仅允许使用 KB/DB 相关工具（retrieve, list_sql_tables, get_tables_schema, read_sql_query）
  - 避免过度检索，智能判断信息充足性
- **适用场景**：数据分析、知识问答、报表生成

### 3. ToolOrchestrator (`ToolOrchestrator/`)
- **功能**：MCP 工具调度系统
- **核心组件**：
  - `ToolRegistry`：工具注册、管理、执行
  - `Security`：权限验证和安全控制
  - `Client`：工具调用客户端
- **工具类型**：
  - **KB Tools**：知识库检索（retrieve）
  - **DB Tools**：数据库操作（list_sql_tables, get_tables_schema, read_sql_query）
  - **Web Search**：联网搜索（web_search）

### 4. RAG Pipeline (`rag/lang_rag.py`)
- **功能**：RAG 检索与知识库管理
- **技术栈**：
  - **Embedding**：multilingual-e5-large (1024维)
  - **Vector DB**：Qdrant (Cosine 相似度)
  - **Text Splitter**：TokenTextSplitter (chunk_size=200, overlap=50)
  - **队列化**：通过 queue_server 避免并发冲突
- **API**：
  - `initialize_from_folder()`: 从文件夹构建知识库
  - `add_file()` / `delete_file()`: 单文件管理
  - `retrieve()`: 向量检索
  - `rerank()`: LLM 重排序（可选）

### 5. Model Manager (`models/model_manager.py`)
- **功能**：全局 Embedding 模型管理器（单例模式）
- **优势**：
  - 避免重复加载模型，节省内存和启动时间
  - 自动 GPU/CPU 选择，显存不足时自动降级
  - 统一管理所有知识库集合
- **API**：
  - `initialize_models()`: 初始化模型和向量数据库
  - `get_embedding_model()`: 获取 Embedding 模型
  - `get_vectorstore(collection_name)`: 获取向量存储实例

---

## 📡 API 文档

### 基础信息
- **Base URL**: `http://localhost:5001`
- **API Prefix**: `/api`

### 1. 流式问答接口

#### `POST /api/qa/stream`

实时流式问答，返回智能体思考过程和工具调用状态。

**Request 示例**
```json
{
  "query": "南美白对虾的最佳养殖密度是多少？",
  "config": {
    "mode": "auto",
    "rag": {
      "collection_name": "japan_shrimp",
      "topk_single": 5
    },
    "single": {
      "temperature": 0.4,
      "max_tokens": 4096
    }
  }
}
```

**Response 示例（SSE 流）**
```
data: {"type": "tool_call", "step": 1, "tool_name": "retrieve", "content": "调用工具: retrieve"}

data: {"type": "thinking", "step": 2, "content": "根据检索结果分析..."}

data: {"type": "final_answer", "step": 3, "content": "南美白对虾的最佳养殖密度为..."}

data: {"status": "final", "answer": "南美白对虾的最佳养殖密度为..."}
```

### 2. 知识库管理接口

#### `POST /api/kb/create`

创建新的知识库。

**Request 示例**
```json
{
  "collection_name": "my_knowledge_base",
  "folder_path": "data/raw_data/my_docs"
}
```

#### `POST /api/kb/add_file`

向知识库添加单个文件。

**Request 示例**
```json
{
  "collection_name": "japan_shrimp",
  "file_path": "data/raw_data/japan_shrimp/new_doc.pdf"
}
```

#### `DELETE /api/kb/delete_file`

从知识库删除文件。

**Request 示例**
```json
{
  "collection_name": "japan_shrimp",
  "file_name": "data/raw_data/japan_shrimp/old_doc.pdf"
}
```

#### `GET /api/kb/list_collections`

列出所有知识库集合。

**Response 示例**
```json
{
  "collections": [
    "japan_shrimp",
    "bank",
    "all_data",
    "knowledge_base"
  ]
}
```

### 3. 直接检索接口

#### `POST /api/kb/retrieve`

直接检索知识库，不经过智能体。

**Request 示例**
```json
{
  "collection_name": "japan_shrimp",
  "query": "溶氧标准",
  "top_k": 5
}
```

**Response 示例**
```json
{
  "chunks": [
    {
      "content": "循环水系统溶氧标准应保持在 5.5 mg/L 以上...",
      "metadata": {
        "source": "japan_shrimp/manual_ch3.pdf",
        "chunk_id": "abc-123"
      },
      "score": 0.89
    }
  ],
  "total": 5
}
```

---

## 🧠 技术栈

### 后端框架
- **Flask**: 轻量级 Web 框架，提供 REST API 和 SSE 支持

### AI 与 LLM
- **OpenAI GPT-4o-mini**: 智能推理、工具选择、自然语言生成
- **LangChain**: AI 应用开发框架，集成 LLM、向量数据库、工具

### Embedding 与向量检索
- **multilingual-e5-large**: 多语言 Embedding 模型（1024维）
- **Qdrant**: 高性能向量数据库（本地部署）
- **sentence-transformers**: Embedding 模型加载与推理

### 数据库
- **MySQL (Aliyun RDS)**: 养殖数据存储
- **aiomysql**: 异步 MySQL 客户端
- **SQLite**: Qdrant 向量数据库底层存储

### 智能体架构
- **ReAct**: 思考-行动-观察循环，自主决策
- **MCP (Model Context Protocol)**: 统一工具调度协议

### 联网搜索
- **Tavily API**: 实时网络搜索与新闻检索

### 数据处理
- **pandas**: 数据分析和处理
- **LangChain Text Splitter**: 文档分块

### 开发工具
- **pydantic**: 数据验证和配置管理
- **python-dotenv**: 环境变量管理
- **logging**: 日志记录

---

## 🧪 测试与验证

### 运行所有测试

```bash
# 进入测试目录
cd tests

# 运行测试套件
python run_tests.py
```

### 单元测试

```bash
# 测试知识库功能
python tests/test_kb.py

# 测试 SQL Agent
python tests/test_sql_agent.py

# 测试联网搜索
python tests/test_web_search.py

# 测试 SSE 服务
python tests/test_server_sse.py
```

### 基准测试

```bash
# 运行问答评估
python benchmark/eval_stream_qa.py
```

评估结果将保存在 `benchmark/results/` 目录。

### 手动测试

```bash
# 测试 DataAgent
python run_data_agent.py

# 测试知识库问答
python run_qa/lang_kb_qa.py

# 测试工作流
python run_flow.py
```

---

## 🌍 部署指南

### 本地部署

```bash
# 激活环境
conda activate camel_agent

# 启动服务
python api/main.py
```

服务将在 `http://localhost:5001` 上运行。

### Docker 部署

```dockerfile
# Dockerfile 示例
FROM python:3.10-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY . /app

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 暴露端口
EXPOSE 5001

# 启动命令
CMD ["python", "api/main.py"]
```

构建并运行：
```bash
docker build -t camel_agent .
docker run -p 5001:5001 \
  -e OPENAI_API_KEY=your_key \
  -e TAVILY_API_KEY=your_key \
  -v $(pwd)/data:/app/data \
  camel_agent
```

### 生产环境部署建议

1. **使用 Gunicorn 作为 WSGI 服务器**：
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5001 api.main:app
```

2. **配置 Nginx 反向代理**：
```nginx
server {
    listen 80;
    server_name your_domain.com;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/qa/stream {
        proxy_pass http://127.0.0.1:5001;
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        chunked_transfer_encoding off;
    }
}
```

3. **使用 Supervisor 进程管理**：
```ini
[program:camel_agent]
command=/path/to/conda/envs/camel_agent/bin/gunicorn -w 4 -b 0.0.0.0:5001 api.main:app
directory=/path/to/Camel_agent
user=your_user
autostart=true
autorestart=true
stderr_logfile=/var/log/camel_agent.err.log
stdout_logfile=/var/log/camel_agent.out.log
```

---

## ❓ 常见问题

### Q1: 启动时报 `CUDA out of memory`

**A**: Embedding 模型尝试使用 GPU 但显存不足。解决方案：

```python
# 修改 models/model_manager.py，强制使用 CPU
model_manager.initialize_models(
    embedding_model_path="models/multilingual-e5-large",
    device="cpu"  # 强制使用 CPU
)
```

或在 `api/main.py` 中修改：
```python
model_manager.initialize_models(
    embedding_model_path="models/multilingual-e5-large",
    vector_persist_path="data/vector_data",
    vector_size=1024,
    device="cpu"  # 添加此参数
)
```

### Q2: 启动后无法访问 `http://localhost:5001`

**A**: 检查端口是否被占用或防火墙设置。

```bash
# 检查端口占用
lsof -i :5001

# 修改端口（在 api/main.py 最后一行）
app.run(host='0.0.0.0', port=8080, debug=True, use_reloader=False)
```

### Q3: `OPENAI_API_KEY not found`

**A**: 确保 `.env` 文件存在且配置正确。

```bash
# 检查 .env 文件
cat .env

# 或直接在终端导出
export OPENAI_API_KEY=your_api_key_here
```

### Q4: 知识库检索结果不准确

**A**: 可能需要调整检索参数或重新构建向量索引。

```python
# 调整 top_k 值
lang_rag = LangRAG(collection_name="japan_shrimp")
results = lang_rag.retrieve(query="养殖密度", k=10)  # 增加检索数量

# 或调整 chunk_size
lang_rag = LangRAG(
    collection_name="japan_shrimp",
    chunk_size=300,  # 增大分块大小
    chunk_overlap=100
)
```

### Q5: Agent 陷入循环，重复调用工具

**A**: 调整 Agent 的最大步数或工具调用次数限制。

```python
# 在 agents/mcp_toolcall_agent.py 中修改
class MCPToolCallAgent(ReActAgent):
    max_tool_calls: int = 5  # 减少最大工具调用次数
```

### Q6: MySQL 连接失败

**A**: 检查数据库配置和网络连接。

```python
# 修改 ToolOrchestrator/tools/db_tools.py 中的配置
DB_CONFIG = {
    "host": "your_mysql_host",
    "user": "your_user",
    "password": "your_password",
    "db": "your_database"
}
```

---

## 📜 版本记录

| 版本号 | 日期       | 更新内容                                                     |
| ------ | ---------- | ------------------------------------------------------------ |
| v2.0.0 | 2025-10-29 | 重构为 MCP 工具调度架构，引入 ReAct Agent，优化流式输出     |
| v1.5.0 | 2025-10-20 | 新增全局模型管理器，队列化 RAG，提升并发稳定性               |
| v1.4.0 | 2025-10-15 | 集成 Tavily 联网搜索功能，支持 SSE 流式响应                  |
| v1.3.0 | 2025-10-10 | 新增 DataAgent，支持知识库 + 数据库多源数据分析              |
| v1.2.0 | 2025-09-28 | 引入 LangChain + Qdrant 向量检索                             |
| v1.1.0 | 2025-09-20 | 支持 MySQL 数据库查询工具                                    |
| v1.0.0 | 2025-09-10 | 完成基础 RAG 问答与知识库管理功能                            |

---

## 📄 许可证

本项目采用 [MIT License](LICENSE)。

---

## 🙏 致谢

特别感谢以下开源项目和技术：

- [OpenAI](https://openai.com) - 提供强大的 LLM 能力
- [LangChain](https://github.com/langchain-ai/langchain) - AI 应用开发框架
- [Qdrant](https://qdrant.tech) - 高性能向量数据库
- [sentence-transformers](https://www.sbert.net) - Embedding 模型库
- [Tavily](https://tavily.com) - 联网搜索 API
- [Flask](https://flask.palletsprojects.com) - Web 框架
- [Hugging Face](https://huggingface.co) - 模型托管平台

---

## 📧 联系方式

如有问题或建议，请通过以下方式联系：

- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Email**: your-email@example.com

---

**✨ Happy Coding! 🦐**
