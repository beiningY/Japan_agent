from openai import OpenAI
import os
from dotenv import load_dotenv
from rag.lang_rag import LangRAG  # RAG 向量检索
import asyncio

load_dotenv()
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# 初始化 RAG
rag = LangRAG(
    persist_path="data/vector_data",
    collection_name="japan_shrimp"  
)

# 查询示例
query = "当前监测显示：DO=3.4 mg/L，比昨日下降了 0.8 单位，pH=8.0，水温 28.5°C。请问是否需要立即调整供氧或循环策略？如果需要，应优先采取哪些操作？"

# 先做 RAG 检索
context = build_rag_context(query)

# 调用 OpenAI Responses API
response = client.responses.create(
    model="gpt-5",
    instructions="你是一个专家AI",
    input=context,
)

# 打印结果
print(response.output_text)
