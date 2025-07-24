# 创建并初始化一个向量数据库 (以QdrantStorage为例)
from camel.storages.vectordb_storages import QdrantStorage
from camel.embeddings import SentenceTransformerEncoder
from camel.retrievers import VectorRetriever
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

embedding_model=SentenceTransformerEncoder(model_name="models/multilingual-e5-large")


vector_storage = QdrantStorage(
    vector_dim=embedding_model.get_output_dim(),
    path="data/knowledge_bank",
    collection_name="bank"
)

vr = VectorRetriever(embedding_model=embedding_model, storage=vector_storage)
"""for i in os.listdir('data/raw_data/bank/bank'):
    content = 'data/raw_data/bank/bank/'+i
    print(content)
    if i.endswith('.pdf'):
        vr.process(
            content=content, 
            storage=vector_storage
        )
"""

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")
os.environ["TOKENIZERS_PARALLELISM"] = "false"


agent = ChatAgent(
    system_message="你是一个金融专家，请根据用户的问题和相关的知识库内容，给出专业的回答。",
    model=ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
        api_key=os.getenv("GPT_API_KEY"),
        model_config_dict={"temperature": 0.4, "max_tokens": 4096},
    )
)
while True:
    qus=input("请输入问题：")
    text=""
    results = vr.query(
    query=qus,
    top_k=4
)
    for num,i in enumerate(results):
        text+=f"第{num+1}个相关内容：{i['text']}\n"
    query=f"""用户的问题是：{qus}\n
    "相关的知识库内容是：{text}\n"""
    print(results)
    print(text)
    print(agent.step(query).msg.content)
    metadata=[]
    for i in results:
        metadata.append(i['content path'])
    print("来源文档 metadata:\n", metadata)
