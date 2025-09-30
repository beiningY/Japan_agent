import sys
import os
# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcp.server import FastMCP
import asyncio
from ToolOrchestrator.tools.kb_tools import create, delete, ask, add_file, deletefile, retrieve
import logging
logger = logging.getLogger("kb_server")
logger.setLevel(logging.INFO)
# 向其他智能体提供知识库操作工具
# 初始化 MCP Server

server = FastMCP(
    name="kb-mcp-server",
    instructions="""
    This server provides knowledge base management.
    You can create, delete, and query knowledge bases.
    You can also add and delete files from the knowledge base.
    """
    )

# 注册工具
@server.tool(    
    name="create_collection",
    description="创建一个新的类型的知识库")
async def create_collection(collection_name: str):
    return create(collection_name)

@server.tool(
    name="delete_collection",
    description="删除指定的知识库集合")
async def delete_collection(collection_name: str):
    return delete(collection_name)


@server.tool(
    name="create_file",
    description="向量化一个文件")
async def create_file(collection_name: str, file_path: str):
    return add_file(collection_name, file_path)

@server.tool(
    name="delete_file",
    description="删除一个已向量化的文件")
async def delete_file(collection_name: str, file_path: str):
    return deletefile(collection_name, file_path)


@server.tool(
    name="retrieve",
    description="从指定知识库检索 top-k 语义相关片段（不经 LLM）"
)
async def retrieve_chunks(collection_name: str, question: str, k: int = 5):
    return retrieve(collection_name=collection_name, question=question, k=k)
 
if __name__ == "__main__":
    if asyncio.iscoroutine(server.run()):  
        asyncio.run(server.run())
