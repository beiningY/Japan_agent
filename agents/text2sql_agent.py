from agents.base import BaseAgent
from rag.lang_rag import LangRAG
from langchain_openai import ChatOpenAI
import os
import logging

logger = logging.getLogger("LangSingleAgent")
logger.setLevel(logging.INFO)

# Agent 创建 sql agent 调用mcp为工具进行数据库查询和分析

from langchain import hub
# 定义sqlagent的prompt
prompt_template = hub.pull("langchain-ai/sql-agent-system-prompt")
assert len(prompt_template.messages) == 1
prompt_template.messages[0].pretty_print()
system_message = prompt_template.format(dialect="MySQL", top_k=5)

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
# 在内存中管理对话历史
memory = MemorySaver()
# 编译Agent
graph = create_react_agent(llm, state_modifier=system_message, checkpointer=memory)
# 接口函数
from langchain_core.messages import RemoveMessage, AIMessage, HumanMessage, ToolMessage
import dotenv
dotenv.load_dotenv()
recursion_limit = 5

# 用户session对象
def user_config(sessionId):
    config = {"configurable": {"thread_id": sessionId, "recursion_limit":recursion_limit}}
    return config


# 获取对话的上下文
def get_messages(sessionId):
    config = user_config(sessionId)
    messages = graph.get_state(config).values["messages"]
    return messages

# 格式化输出
def format(messages):
    resp = ""
    i = 0
    for message in messages:
        # 函数调用的AIMessage和ToolMessage不输出显示
        if isinstance(message, AIMessage) and len(message.content)>0:
            resp = resp+"AI: "+message.content+"\n"
            if i>1 and isinstance(messages[i-1], ToolMessage) \
                and (messages[i-1].name == "sql_db_query"):
                resp = resp+"\n<a href='javascript:showInfo(\""+str(i)+"\""+")'>查看执行过程</a>\n"
            resp = resp+"\n"
        if isinstance(message, HumanMessage):
            resp = resp+"User: "+message.content+"\n"
        i= i+1
    resp = resp.replace("\n","<br/>")
    return resp

# 对话
def ask_agent(query,sessionId):
    config = user_config(sessionId)
    inputs = {"messages": [("user", query)]}
    try:
        graph.invoke(inputs, config=config)
        messages = graph.get_state(config).values["messages"]
        # 对话记录格式化输出成文本
        response = format(messages)
    except Exception as e:
        response =  repr(e)
    return response
