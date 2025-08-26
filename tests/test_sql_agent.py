import asyncio
import os
import logging
from agents.sql_agent import init_agent, format_messages, user_config, agent_graph

logger = logging.getLogger("sql_agent")
logger.setLevel(logging.INFO)




async def ask_agent(query: str, sessionId: str) -> str:
    global agent_graph
    if agent_graph is None:
        agent_graph = await init_agent()

    config = user_config(sessionId)
    inputs = {"messages": [("user", query)]}
    try:
        final_state = await agent_graph.ainvoke(inputs, config=config)
        messages = final_state["messages"]
        response = format_messages(messages)
    except Exception as e:
        logger.error(f"Error in ask_agent for session {sessionId}: {e}", exc_info=True)
        response = f"An error occurred: {repr(e)}"
    return response

async def main_chat_loop():
    print("\n====================== MySQL Chat Agent ======================\n")
    print("Ask me questions about your database! Type 'exit' or 'quit' to end.\n")

    session_id = f"session_{os.getpid()}"

    while True:
        user_input = input(f"[{session_id}] > ")
        if user_input.lower() in {"exit", "quit", "q"}:
            break
        
        response = await ask_agent(user_input, session_id)
        print("\n--- Response ---")
        print(response)
        print("-------------------------------------------------------------\n")

if __name__ == "__main__":
    asyncio.run(main_chat_loop())
