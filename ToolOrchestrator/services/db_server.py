import sys
import os
# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
from typing import List
from mcp.server import FastMCP
from ToolOrchestrator.tools.db_tools import list_sql_tables as _list_sql_tables, get_tables_schema as _get_tables_schema, read_sql_query as _read_sql_query
import logging
logger = logging.getLogger("db_server")
logger.setLevel(logging.INFO)
# 向其他智能体提供数据库操作工具
# 初始化 MCP Server

server = FastMCP(
    name="db-mcp-server",
    instructions="""
    This server provides database management tools.
    """
    )
#注册工具
@server.tool(
    name="list_sql_tables",
    description="列出数据库中的所有表"
)
async def list_sql_tables() -> dict:
    return await _list_sql_tables()

@server.tool(
    name="get_tables_schema",
    description="获取一个或多个指定表的结构"
)
async def get_tables_schema(table_names: List[str]) -> dict:
    return await _get_tables_schema(table_names)


@server.tool(
    name="read_sql_query",
    description="执行一个或多个SQL查询"
)
async def read_sql_query(table_queries: list) -> dict:
    return await _read_sql_query(table_queries)

if __name__ == "__main__":
    if asyncio.iscoroutine(server.run()):  
        asyncio.run(server.run())