import os
import logging
from agents.sql_agent import init_agent, format_messages, user_config, agent_graph
import asyncio

logger = logging.getLogger("query_data_with_mcp")
logger.setLevel(logging.INFO)

async def ask_agent(query: str, sessionId: str) -> str:
    global agent_graph
    if agent_graph is None:
        agent_graph = await init_agent()

    config = user_config(sessionId)
    input_query = query 
    inputs = {"messages": [("user", input_query)]}
    try:
        final_state = await agent_graph.ainvoke(inputs, config=config)
        messages = final_state["messages"]
        response = format_messages(messages)
    except Exception as e:
        logger.error(f"会话 {sessionId} 错误: {e}", exc_info=True)
        response = f"错误: {repr(e)}"
    return response

async def main(query):
    session_id = f"session_{os.getpid()}"   
    response = await ask_agent(query, session_id)
    return response

if __name__ == "__main__":
    query = "请问有哪些数据"
    asyncio.run(main(query))
