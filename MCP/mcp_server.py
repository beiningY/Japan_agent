import sys
import os
# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server import FastMCP
from run_qa import create_kb, delete_kb, ask, add_file, delete_file
# 向中枢或其他智能体提供知识库接口管理增删改查功
# 初始化 MCP Server
server = FastMCP(name="kb-mcp-server")
mcp_with_instructions =FastMCP(
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
    return create_kb(collection_name)

@server.tool(
    name="delete_collection",
    description="删除指定的知识库集合")
async def delete_collection(collection_name: str):
    return delete_kb(collection_name)


@server.tool(
    name="create_file",
    description="向量化一个文件")
async def create_file(collection_name: str, file_path: str):
    return add_file(collection_name, file_path)

@server.tool(
    name="delete_file",
    description="删除一个已向量化的文件")
async def delete_file(collection_name: str, file_path: str):
    return delete_file(collection_name, file_path)


@server.tool(
    name="ask",
    description="向知识库提问")
async def ask(collection_name: str, question: str):
    return ask(collection_name, question)
 
# 启动 MCP 服务端
server.run()
