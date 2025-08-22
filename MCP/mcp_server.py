# mcp_server.py
from mcp.server import MCPServer
from run_qa.lang_kb_qa import create_kb, delete_kb
from rag.lang_rag import add_file, delete_file
# 向中枢或其他智能体提供知识库接口管理增删改查功
# 初始化 MCP Server
server = MCPServer()

# 注册工具
server.register_tool(
    name="create_collection",
    description="创建一个新的类型的知识库",
    func=create_kb,
    input_schema={"collection_name": str}
)

server.register_tool(
    name="delete_collection",
    description="删除指定的知识库集合",
    func=delete_kb,
    input_schema={"collection_name": str}
)

server.register_tool(
    name="list_collections",
    description="列出所有知识库集合",
    func=list_collections,
    input_schema={"collection_name": str}
)
server.register_tool(
    name="create_file",
    description="向量化一个文件",
    func=add_file,
    input_schema={"collection_name": str, "file_path": str}
)

server.register_tool(
    name="delete_file",
    description="删除一个已向量化的文件",
    func=delete_file,
    input_schema={"collection_name": str, "file_path": str}
)


# 启动 MCP 服务端
server.start()
