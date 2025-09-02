from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
import asyncio
import dotenv
dotenv.load_dotenv()
import logging
logger = logging.getLogger("db_client")
logger.setLevel(logging.INFO)

async def client():
    client_mcp = MultiServerMCPClient(
        {
            "db-mcp-server": {
                "command": "python",
                "args": ["/usr/sarah/Camel_agent/MCP/db_server.py"],
                "transport": "stdio",
            }
        }
    )
    tools = await client_mcp.get_tools()
    logger.info(f"查询到的工具: {tools}")
    tool_names_to_use = {
    "list_sql_tables",
    #"get_tables_schema",
    #"read_sql_query",
    }
    allowed_tools = [t for t in tools if t.name in tool_names_to_use]
    return allowed_tools
    # agent = create_react_agent("openai:gpt-4o-mini", allowed_tools)
    # response = await agent.ainvoke({"messages": "传感器测量的六月二十八号凌晨的温度是多少"})
    # logger.info(response)

if __name__ == "__main__":
    asyncio.run(client())