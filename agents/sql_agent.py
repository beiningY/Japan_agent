import logging
from typing import List
from dotenv import load_dotenv
from langchain import hub
from langchain_core.messages import (
    AIMessage, AnyMessage, HumanMessage, ToolMessage
)
from langchain_core.messages.utils import count_tokens_approximately, trim_messages
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState
from MCP.db_client import load_sql_tools
from langchain_core.tools import tool
import os

logger = logging.getLogger("sql_agent")
logger.setLevel(logging.INFO)

if load_dotenv():
    print("✅ Loaded .env file")
else:
    print("⚠️ No .env file found")


# Memory & Config
agent_graph = None
agent_memory = InMemorySaver()
recursion_limit = 3

def user_config(sessionId):
    return {"configurable": {"thread_id": sessionId, "recursion_limit": recursion_limit}}

def pre_model_hook(state: AgentState) -> dict[str, list[AnyMessage]]:
    trimmed_messages = trim_messages(
        state["messages"],
        strategy="last",
        token_counter=count_tokens_approximately,
        max_tokens=30000,
        start_on="human",
        end_on=("human", "tool"),
        include_system=True,
    )
    return {"llm_input_messages": trimmed_messages}

async def init_agent():
    """初始化 SQL Agent"""
    global agent_graph
    global agent_memory
    # LLM
    llm = ChatOpenAI(model="gpt-4o", temperature=0.4)

    # System Prompt
    prompt_template = hub.pull("langchain-ai/sql-agent-system-prompt")
    SYSTEM_PROMPT = prompt_template.messages[0].prompt.template.format(
    dialect="MySQL", top_k=10
)
    if agent_graph is not None:
        return agent_graph

    print("🚀 Initializing Agent...")
    allowed_tools = await load_sql_tools()
    agent_graph = create_react_agent(
        llm,
        allowed_tools,
        pre_model_hook=pre_model_hook,
        checkpointer=agent_memory,
        prompt=SYSTEM_PROMPT,
    )
    print("✅ Agent initialized successfully.")
    return agent_graph

def format_messages(messages: List[AnyMessage]) -> str:
    """只返回最终AI回答，过程写入日志"""
    final_answer = None

    for i, message in enumerate(messages):
        if isinstance(message, HumanMessage):
            logger.info(f"User: {message.content}")
        elif isinstance(message, AIMessage):
            if message.content:  # 只有有内容时才认为是回答
                final_answer = message.content
            logger.info(f"AI: {message.content or '[Tool call / intermediate step]'}")
        elif isinstance(message, ToolMessage):
            logger.info(f"Tool[{message.name}]: {message.content}")

    # 如果有最终回答，返回它；否则返回空字符串
    return f"根据sql查询后智能体的回答是: {final_answer}" if final_answer else ""
