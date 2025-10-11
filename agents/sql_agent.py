"""
注意：此文件为旧版实现，已被 DataAgent 的 MCP 工具方式替代。
建议使用 agents/data_agent.py 进行数据库查询。
此文件仅保留用于向后兼容和测试。
"""
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
from ToolOrchestrator.client import client
from langchain_core.tools import tool
import asyncio
import os
logger = logging.getLogger("sql_agent")
logger.setLevel(logging.INFO)


agent_graph = None
agent_memory = InMemorySaver()


def user_config(sessionId):
    return {"configurable": {"thread_id": sessionId, "recursion_limit": 30}}

def pre_model_hook(state: AgentState) -> dict[str, list[AnyMessage]]:
    """在调用LLM之前，对历史消息进行修剪和整理"""
    trimmed_messages = trim_messages(
        state["messages"],
        strategy="last",
        token_counter=count_tokens_approximately,
        max_tokens=3000,
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

    # 设置text2sql的系统消息
    """
    system
    You are an agent designed to interact with a SQL database.
    Given an input question, create a syntactically correct {dialect} query to run, then look at the results of the query and return the answer.
    Unless the user specifies a specific number of examples they wish to obtain, always limit your query to at most {top_k} results.
    You can order the results by a relevant column to return the most interesting examples in the database.
    Never query for all the columns from a specific table, only ask for the relevant columns given the question.
    You have access to tools for interacting with the database.
    Only use the below tools. Only use the information returned by the below tools to construct your final answer.
    You MUST double check your query before executing it. If you get an error while executing a query, rewrite the query and try again.
    DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.
    To start you should ALWAYS look at the tables in the database to see what you can query.
    Do NOT skip this step.
    Then you should query the schema of the most relevant tables.
    """
    prompt_template = hub.pull("langchain-ai/sql-agent-system-prompt")
    SYSTEM_PROMPT = prompt_template.messages[0].prompt.template.format(
    dialect="MySQL", top_k=10
)
    if agent_graph is not None:
        return agent_graph

    logger.info("智能体初始化...")
    allowed_tools = await client()
    agent_graph = create_react_agent(
        llm,
        allowed_tools,
        pre_model_hook=pre_model_hook,
        checkpointer=agent_memory,
        prompt=SYSTEM_PROMPT,
    )
    logger.info("智能体初始化成功")
    return agent_graph

def format_messages(messages: List[AnyMessage]) -> str:
    """只返回最终AI回答，过程写入日志"""
    final_answer = None

    for i, message in enumerate(messages):
        if isinstance(message, HumanMessage):
            logger.info(f"User: {message.content}")
        elif isinstance(message, AIMessage):
            if message.content: 
                final_answer = message.content
            logger.info(f"AI: {message.content or '[Tool call / intermediate step]'}")
        elif isinstance(message, ToolMessage):
            logger.info(f"Tool[{message.name}]: {message.content}")

    return f"根据sql查询后智能体的回答是: {final_answer}" if final_answer else ""

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
    query = "请问传感器可以测量哪些数据"
    asyncio.run(main(query))