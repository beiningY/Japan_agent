import asyncio
import os
import logging
from typing import List

from dotenv import load_dotenv
from langchain import hub
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    HumanMessage,
    ToolMessage,
)
from langchain_core.messages.utils import count_tokens_approximately, trim_messages
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.exceptions import McpError

# --- 日志和环境配置 ---
logger = logging.getLogger("LangMySQLAgent")
logger.setLevel(logging.INFO)

if load_dotenv():
    print("✅ Loaded .env file")
else:
    print("⚠️ No .env file found")

# --- 核心组件实例化 ---
# 确保你的 .env 文件中有 OPENAI_API_KEY
llm = ChatOpenAI(model="gpt-4o", temperature=0)

# --- MCP 服务器参数 ---
# 未来可以考虑将此路径放入环境变量
MCP_SERVER_SCRIPT_PATH = "/usr/henry/cognitive-center/mcp_server/main.py"

SQL_MCP_SERVER_PARAMS = StdioServerParameters(
    command="python",
    args=[MCP_SERVER_SCRIPT_PATH],
    env={
        "MCP_SERVER_NAME": "cognitive-mcp-server",
        "MCP_LOG_LEVEL": "INFO",
    }
)

prompt_template = hub.pull("langchain-ai/sql-agent-system-prompt")
DIALECT = "MySQL"
TOP_K = 10
SYSTEM_PROMPT = prompt_template.messages[0].prompt.template.format(
    dialect=DIALECT, top_k=TOP_K
)

# --- 预处理和 Agent 配置 (保持不变) ---
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

agent_graph = None
agent_memory = InMemorySaver()
recursion_limit = 3

def user_config(sessionId):
    return {"configurable": {"thread_id": sessionId, "recursion_limit": recursion_limit}}

# --- Agent 初始化 ---
async def init_agent():
    global agent_graph
    global agent_memory

    if agent_graph is not None:
        print("✅ Agent already initialized.")
        return

    print("🚀 Initializing Agent...")
    try:
        # 启动 MCP 客户端并加载工具
        async with stdio_client(SQL_MCP_SERVER_PARAMS) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("✅ Successfully connected to cognitive-mcp-server")
                
                mcp_tools = await load_mcp_tools(session)
                
                # 打印从您的服务器发现的所有工具，以便核对
                discovered_tool_names = [t.name for t in mcp_tools]
                print(f"📌 Discovered tools from your server: {discovered_tool_names}")

                # **关键步骤**: 定义我们希望代理使用的工具名称
                # 请核对上面的打印输出，确保这些名称是正确的！
                tool_names_to_use = {
                    "list_sql_tables",
                    "get_sql_schema",
                    "read_sql_query",
                }
                
                allowed_tools = [
                    tool for tool in mcp_tools if tool.name in tool_names_to_use
                ]

                if len(allowed_tools) != len(tool_names_to_use):
                    print(f"⚠️ Warning: Not all desired tools were found. Expected: {tool_names_to_use}. Found: {[t.name for t in allowed_tools]}")

                print(f"🛠️  Agent will use the following tools: {[tool.name for tool in allowed_tools]}")

                # 创建 ReAct 代理
                agent_graph = create_react_agent(
                    llm,
                    allowed_tools,
                    pre_model_hook=pre_model_hook,
                    checkpointer=agent_memory,
                    prompt=SYSTEM_PROMPT,
                )
                print("✅ Agent initialized successfully.")

    except McpError as e:
        print(f"❌ MCP Error during initialization: {e}")
        raise
    except Exception as e:
        print(f"❌ A general error occurred during initialization: {e}")
        raise

# --- 交互函数 (保持不变) ---
def format_messages(messages: List[AnyMessage]) -> str:
    resp = ""
    i = 0
    for message in messages:
        if isinstance(message, AIMessage) and message.content:
            resp += f"AI: {message.content}<br/>"
            # 确保这里的工具名 'read_sql_query' 与您的服务器提供的名称一致
            if i > 1 and isinstance(messages[i-1], ToolMessage) and (messages[i-1].name == "read_sql_query"):
                resp += f"<a href='javascript:showInfo(\"{i}\")'>查看执行过程</a><br/>"
            resp += "<br/>"
        elif isinstance(message, HumanMessage):
            resp += f"User: {message.content}<br/>"
        i += 1
    return resp

async def ask_agent(query: str, sessionId: str) -> str:
    global agent_graph
    if agent_graph is None:
        await init_agent()

    config = user_config(sessionId)
    inputs = {"messages": [("user", query)]}
    try:
        final_state = await agent_graph.invoke(inputs, config=config)
        messages = final_state["messages"]
        response = format_messages(messages)
    except Exception as e:
        logger.error(f"Error in ask_agent for session {sessionId}: {e}", exc_info=True)
        response = f"An error occurred: {repr(e)}"
    return response

# --- 示例运行 ---
async def main_chat_loop():
    print("\n===================================== MySQL Chat Agent =====================================\n")
    print("Ask me questions about your database! Type 'exit' or 'quit' to end.")

    session_id = f"session_{os.getpid()}" # 创建一个简单的会话ID

    while True:
        user_input = input(f"[{session_id}] > ")
        if user_input.lower() in {"exit", "quit", "q"}:
            break
        
        response = await ask_agent(user_input, session_id)
        # 模拟网页输出
        print("\n--- Response ---")
        print(response.replace("<br/>", "\n"))
        print("----------------\n")


if __name__ == "__main__":
    asyncio.run(main_chat_loop())