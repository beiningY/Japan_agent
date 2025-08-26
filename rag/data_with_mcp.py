import os
import logging
from agents.sql_agent import init_agent, format_messages, user_config, agent_graph

logger = logging.getLogger("query_data_with_mcp")
logger.setLevel(logging.INFO)

def ask_agent(query: str, sessionId: str) -> str:
    global agent_graph
    if agent_graph is None:
        agent_graph = init_agent()

    config = user_config(sessionId)
    input_query = query + "\n请在回答时同时返回在数据库里查询到的数据并根据问题进行分析和回答"
    inputs = {"messages": [("user", input_query)]}
    try:
        final_state = agent_graph.invoke(inputs, config=config)
        messages = final_state["messages"]
        response = format_messages(messages)
    except Exception as e:
        logger.error(f"会话 {sessionId} 错误: {e}", exc_info=True)
        response = f"错误: {repr(e)}"
    return response

def main(query):
    session_id = f"session_{os.getpid()}"   
    response = ask_agent(query, session_id)
    return response

if __name__ == "__main__":
    main(query)
