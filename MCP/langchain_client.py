from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
import asyncio
import dotenv
dotenv.load_dotenv()

async def main():
    client = MultiServerMCPClient(
        {
            "rag-mcp-server": {
                "command": "python",
                # Make sure to update to the full absolute path to your math_server.py file
                "args": ["/Users/sarah/工作/AgentRag/Camel_agent/MCP/mcp_server.py"],
                "transport": "stdio",
            }
        }
    )
    tools = await client.get_tools()
    agent = create_react_agent("openai:gpt-4o-mini", tools)
    weather_response = await agent.ainvoke({"messages": "what is the weather in nyc?"})
    print(weather_response)

if __name__ == "__main__":
    asyncio.run(main())