import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.exceptions import McpError
from langchain_mcp_adapters.tools import load_mcp_tools

# MCP 服务器路径（可放到 .env）
MCP_SERVER_SCRIPT_PATH = "/usr/henry/cognitive-center/mcp_server/main.py"

SQL_MCP_SERVER_PARAMS = StdioServerParameters(
    command="python",
    args=[MCP_SERVER_SCRIPT_PATH],
    env={
        "MCP_SERVER_NAME": "cognitive-mcp-server",
        "MCP_LOG_LEVEL": "INFO",
    }
)

async def load_sql_tools():
    """连接 MCP 并返回 SQL 工具列表"""
    try:
        async with stdio_client(SQL_MCP_SERVER_PARAMS) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("✅ 成功连接到cognitive-mcp-server")

                mcp_tools = await load_mcp_tools(session)
                discovered_tool_names = [t.name for t in mcp_tools]
                print(f"📌 发现工具: {discovered_tool_names}")

                tool_names_to_use = {
                    "list_sql_tables",
                    "get_sql_schema",
                    "read_sql_query",
                }
                allowed_tools = [t for t in mcp_tools if t.name in tool_names_to_use]

                if len(allowed_tools) != len(tool_names_to_use):
                    print(f"⚠️ MCP 错误: 没有找到sql agent全部的需求工具. "
                          f"Expected {tool_names_to_use}, Found {[t.name for t in allowed_tools]}")

                return allowed_tools
    except McpError as e:
        print(f"❌ MCP 错误: {e}")
        raise
    except Exception as e:
        print(f"❌ MCP错误: {e}")
        raise
