
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


# 🦐 ShrimpRAG Assistant
> **一款基于 CAMEL 多智能体 + RAG 的南美白对虾养殖智能问答与分析系统**

---

## 📚 目录（Table of Contents）
- [项目简介](#-项目简介)
- [功能特性](#-功能特性)
- [系统架构](#-系统架构)
- [快速开始](#-快速开始)
- [环境配置](#-环境配置)
- [核心模块说明](#-核心模块说明)
- [API 文档](#-api-文档)
- [算法与模型](#-算法与模型)
- [测试与验证](#-测试与验证)
- [部署指南](#-部署指南)
- [常见问题](#-常见问题)
- [版本记录](#-版本记录)
- [许可证](#-许可证)
- [致谢](#-致谢)

---

## 📝 项目简介
**ShrimpRAG Assistant** 是一款智能化知识问答与分析系统，旨在为南美白对虾养殖户及科研人员提供：
- 📖 **快速检索**：秒级搜索养殖手册中的设计规范  
- 🤖 **智能推理**：基于 CAMEL 多智能体进行专家级回答  
- 📊 **数据分析**：对社交媒体聚类文本进行消费者心理与因果分析  
- 📑 **自动报告**：生成 PDF/Word 格式的决策支持报告  

> 本项目面向 **农业 AI 助手、知识检索、数据分析** 等场景，支持本地化部署。

---

## ✨ 功能特性
- 🔎 **混合检索**：BM25 + FAISS + Rerank 提供精准上下文  
- 🧠 **多智能体协作**：基于 CAMEL 的 Expert AI 与 Helper AI  
- 📈 **统计建模**：支持词频统计、词云可视化、因果推导  
- 📂 **文档导入**：支持 PDF/Docx 解析与结构化 Chunk 划分  
- 📡 **开放 API**：RESTful 接口便于集成其他系统  
- ⚡ **轻量部署**：支持 Conda & Docker 一键部署  
- 🌐 **多语言支持**：支持中英文问题解析与回答  

---

## 🏗 系统架构
![系统架构图](docs/architecture.png)

**架构说明：**
1. **前端 UI**：基于 Gradio 提供交互界面  
2. **API 服务**：使用 FastAPI 提供 REST 接口  
3. **检索层**：BM25 + FAISS 混合检索与 Rerank  
4. **多智能体**：CAMEL RolePlaying（Expert AI & Helper AI）  
5. **模型层**：Qwen-72B 用于推理与报告生成  
6. **数据存储**：SQLite + 向量数据库  

---

## 🚀 快速开始

### 1. 克隆项目
```bash
git clone https://github.com/your-org/shrimp-rag-assistant.git
cd shrimp-rag-assistant
````

### 2. 创建虚拟环境并安装依赖

```bash
conda create -n shrimp_agent python=3.10
conda activate shrimp_agent
pip install -r requirements.txt
```

### 3. 启动服务

```bash
python app.py
```

> 访问 `http://localhost:7860` 查看 Web UI。

---

## 💻 环境配置

* **Python**: >= 3.10
* **CUDA**: >= 11.8 (推荐 GPU 推理)
* **内存**: >= 16GB
* **主要依赖**：

```txt
fastapi==0.115.0
gradio==4.41.0
faiss-cpu==1.8.0
camel-ai==0.2.3
qwen==1.7.0
```

---

## 🔍 核心模块说明

| 模块名                | 描述                        | 输入        | 输出          |
| ------------------ | ------------------------- | --------- | ----------- |
| `file_parser.py`   | 解析 PDF/Docx，进行章节 Chunk 划分 | PDF 路径    | JSON（结构化数据） |
| `rag_retriever.py` | 使用 BM25+FAISS 检索相关知识块     | 用户问题      | Top-k 文本块   |
| `agents/`          | CAMEL 多智能体协作回答            | 问题 + 检索结果 | 回答文本        |
| `report_gen.py`    | 分析聚类文本并生成心理学因果分析报告        | 聚类文本数据    | Word/PDF 报告 |
| `api.py`           | 提供 RESTful API            | JSON 请求   | JSON 响应     |

---

## 📡 API 文档

### `POST /api/ask`

* **描述**：智能问答接口
* **Request 示例**

```json
{
  "question": "循环水系统溶氧标准是多少？"
}
```

* **Response 示例**

```json
{
  "answer": "建议保持 5.5 mg/L 以上，以确保虾类健康生长。"
}
```

### `POST /api/report`

* **描述**：生成消费者心理分析报告
* **Request 示例**

```json
{
  "cluster_file": "clusters.csv"
}
```

* **Response 示例**

```json
{
  "report_path": "output/report_2025-09-28.docx"
}
```

---

## 🧠 算法与模型

* **嵌入模型**：BERT-base，用于句向量计算
* **聚类算法**：KMeans（k=15）
* **大语言模型**：Qwen-72B-Chat，用于总结与推理
* **评估指标**：

  * Diarization Error Rate (DER)：7.5%
  * Word Error Rate (WER)：12.4%

---

## 🧪 测试与验证

```bash
pytest tests/
```

示例输出：

```
tests/test_rag.py .......   [100%]
tests/test_agent.py ...    [ 90%]
```

---

## 🌍 部署指南

### 本地部署

```bash
python app.py
```

### Docker 部署

```bash
docker build -t shrimp_agent .
docker run -p 7860:7860 shrimp_agent
```

---

## ❓ 常见问题

**Q:** 启动时报 `CUDA not found`
**A:** 安装 GPU 驱动并导出环境变量：

```bash
export PATH=/usr/local/cuda/bin:$PATH
```

**Q:** 启动后无法访问 `http://localhost:7860`
**A:** 检查防火墙与端口是否开放。

---

## 📜 版本记录

| 版本号    | 日期         | 更新内容                       |
| ------ | ---------- | -------------------------- |
| v1.2.0 | 2025-09-28 | 新增消费者心理分析与报告生成功能           |
| v1.1.0 | 2025-09-20 | 引入 BM25+FAISS 混合检索与 Rerank |
| v1.0.0 | 2025-09-10 | 完成基础 RAG 问答与 PDF 解析功能      |

---

## 📄 许可证

本项目采用 [MIT License](LICENSE)。

---

## 🙏 致谢

特别感谢以下开源项目和团队：

* [CAMEL-AI](https://github.com/camel-ai/camel)
* [Qwen](https://qwen.ai)
* [FAISS](https://github.com/facebookresearch/faiss)
* [Gradio](https://gradio.app)

```

---

✨ **使用方法**  
1. 新建 `README.md` 文件，把以上内容完整复制进去。  
2. 修改标题、依赖版本、API 示例、架构图链接等为你项目的实际情况。  
3. 在 `docs/` 目录下保存架构图文件，例如 `architecture.png` 并保持路径一致。  

需要我帮你把这份 README 打包成一个可下载的 Markdown 文件吗？
```
