"""
MCP 客户端示例
用于连接并调用 cognitive-mcp-server
目的是用于调用数据库进行查询功能
"""

import asyncio
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters
from mcp.shared.exceptions import McpError

async def run_client():
    # 启动服务端进程 (绝对路径)
    server_params = StdioServerParameters(
        command="python",
        args=["/usr/henry/cognitive-center/mcp_server/main.py"],
        env={
            "MCP_SERVER_NAME": "cognitive-mcp-server",
            "MCP_LOG_LEVEL": "INFO"
        }
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            try:
                # 初始化会话
                await session.initialize()
                print("✅ 已连接到 MCP 服务端")

                # 获取服务端的工具列表
                tools = await session.list_tools()
                print("📌 服务端工具列表:")
                for t in tools.tools:
                    print(f" - {t.name}: {t.description}")

            except McpError as e:
                print(f"❌ MCP 错误: {e}")
            except Exception as e:
                print(f"❌ 客户端异常: {e}")

if __name__ == "__main__":
    asyncio.run(run_client())
