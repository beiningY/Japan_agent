
## 项目
多轮对话场景：基于 CAMEL 框架实现，支持多角色、多轮交互（如user、 assistant、 critical、 planner）。

RAG 检索增强：基于 LangChain 构建，支持向量检索与 Prompt 拼接方式。Langchain+Camel

插件化架构：单次对话、多场景分析、RAG 检索等均以插件形式存在，可灵活组合与替换。

## 技术栈
对话管理：CAMEL（多智能体角色扮演、多轮对话管理）

检索增强生成：LangChain（RAG Pipeline、向量检索）

API框架：Flask

向量存储：Qdrant（语义检索）

数据处理：Python + Pandas + NLTK手动处理

chat模型调用：OpenAI API 

embeddding模型部署：e5embedding—multilangue bge-large-zh

## 目录结构

CAMEL_AGENT/
│
├── main.py                    # 项目入口，启动API服务或命令行
│
├── config/
│   ├── default_config.yaml     # 默认参数配置（模式选择、超参数、角色设定等）
│   └── prompt_templates/       # Prompt模板文件
│
├── api/                        # 对外API接口
│   ├── routes.py               # 路由定义（FlaskAPI）
│   ├── handlers.py             # API业务处理层
│   └── schemas.py              # 请求/响应参数模型
│
├── data_processing/            # 数据处理脚本
│   ├── clean_book_zh.py           # 数据清洗
│   ├── load_log.py           # 预处理（分词、去噪）
│   └── csv_sql.py      # 人工标注辅助
│   ├── clean_log.py           # 数据清洗

├── embedding/                  # 向量化与向量存储
│   ├── pre_embedding.py    # 后台手动实现向量化到知识库
│   └── auto_embedding.py         # 支持自动向量化到知识库中
│   └── japan_book_chunking.py         # 手动chunking养殖手册
│
├── orchestrator/               # 任务调度器
│   └── task_orchestrator.py    # 根据配置加载并执行插件
│
├── agents/                     # 智能体插件
│   ├── base_agent.py           # 基类
│   ├── single_dialog_agent.py  # 单轮对话
│   ├── multi_scenario_agent.py # 多场景分析（多角色）
│   └── juudge_agent.py
│   └── summarize_agent.py
│   └── plan_agent.py
│   └── text2sql_agent.py
│
├── rag_pipeline/                 # kb的管理+rag功能
│   └── autorag.py       # langchain来进行kb管理+RAG检索+上下文拼接
│   └── handlerag.py       # camel  kb管理+RAG检索+上下文拼接
│
├── utils/                      # 工具函数
│   ├── logger.py               # 日志
│   ├── loader.py               # 配置和Prompt加载
│
├── interface/                      # 前端显示页面
│   ├── gradio.py               # 日志   
│
├── tests/                      # 测试
│   ├── test_api.py
│   ├── test_embedding.py
│   ├── test_agents.py
│   └── test_orchestrator.py
├── run_qa/                      # 测试
│   ├── bank_qa.py    
│   ├── default_qa.py
│   ├── japan_qa.py
│   └── orchestrator.py
│
├── download/            # 下载
└── models/                   # embedding模型
├── requirements.txt            # 依赖
└── README.md                   # 项目说明文件

## 核心架构
### 1. 多轮对话 — CAMEL
支持定义多个角色（如评判家、计划家等）

每个角色有独立的轮数限制与token限制

对话状态由 conversation_memory 管理

### 2. 检索增强生成（RAG） — LangChain
基于 Qdrant向量检索库实现语义搜索

支持 Top-K similirity 检索、Prompt 拼接

可独立调用或嵌入任意 Agent

### 3. 插件化设计
agents/ 目录下的每个 Agent 模块都是独立插件

任务编排器 TaskOrchestrator 根据配置动态加载所需插件

RAG 作为中间件可插入任意对话流程


### 4. 扩展与二次开发
新增 Agent：在 agents/ 目录添加新类，并注册到 API

新增检索方式：在 rag_pipeline/retriever.py 添加新检索逻辑

增加数据处理：在 data_processing/ 目录添加脚本