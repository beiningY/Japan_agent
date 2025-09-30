## ToolOrchestrator 系统详细介绍

### 🏗️ 系统架构概览

ToolOrchestrator 是一个基于 **MCP (Model Control Protocol)** 协议的工具协调网关系统，主要包含以下核心组件：

```
ToolOrchestrator/
├── core/           # 核心模块
│   ├── config.py   # 配置管理
│   └── registry.py # 工具注册器（核心）
├── api/            # HTTP API 接口
│   └── endpoint.py # REST API 端点
├── client/         # MCP 客户端
│   └── client.py   # 多服务器 MCP 客户端
├── services/       # MCP 服务端
│   ├── db_server.py    # 数据库工具服务
│   ├── kb_server.py    # 知识库工具服务
│   └── kb_server_stdio.py
├── tools/          # 工具实现和配置
│   ├── config.json      # 工具配置文件
│   ├── permissions.json # 权限配置文件
│   ├── kb_tools.py      # 知识库工具实现
│   └── db_tools.py      # 数据库工具实现
└── main.py         # 主启动文件
```

### 🔧 核心工作原理

#### 1. 多层架构设计

```
┌─────────────────┐
│   外部 Agent    │ ← HTTP API 调用
├─────────────────┤
│  ToolRegistry   │ ← 工具注册、权限控制、安全包装
├─────────────────┤
│ MultiMCPClient  │ ← MCP 协议通信
├─────────────────┤
│  MCP Services   │ ← 具体工具实现
│ (db/kb/custom)  │
└─────────────────┘
```

#### 2. 工具发现与注册流程

1. **启动阶段**：
   ```python
   # main.py 中的启动流程
   registry = ToolRegistry(mcp_client_config=settings.MCP_CLIENT_CONFIG)
   await registry.initialize_connections()  # 连接所有 MCP 服务端
   registry.load_from_json(settings.TOOLS_CONFIG_PATH)  # 加载工具配置
   ```

2. **工具发现**：
   - `MultiServerMCPClient` 连接配置的 MCP 服务端
   - 从 `tools/config.json` 读取可用工具列表
   - 创建 `MCPTool` 对象表示每个工具

3. **工具注册**：
   - `ToolRegistry` 为每个工具创建安全包装器
   - 添加权限检查、风险评估等安全层
   - 注册到内部工具字典中

#### 3. 安全架构

系统实现了**多层安全控制**：

**第一层：基础权限检查**
```python
# 用户清理级别检查
clearance_map = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
if clearance_map.get(user_clearance.upper(), 0) < clearance_map.get(risk_level.upper(), 0):
    return {"status": "error", "reason": "权限不足"}
```

**第二层：Agent 权限验证**
- 检查 Agent 是否在 `permissions.json` 中注册
- 验证 Agent 是否有权限使用特定工具
- 检查工具是否在受限列表中

**第三层：参数过滤**
```python
# 过滤内部参数，只传递给 MCP 服务端的参数
internal_args = ['user_clearance', 'user_id', 'user_context', 'agent_name']
tool_args = {k: v for k, v in kwargs.items() if k not in internal_args}
```

### 🛠️ Agent 调用工具的方式

#### 方式一：直接 HTTP API 调用

```python
import requests

# 1. 执行工具
response = requests.post(
    "http://localhost:8000/api/tools/execute",
    json={
        "tool_name": "retrive",
        "arguments": {
            "collection_name": "japan_shrimp",
            "question": "请问ph值如何调整？"
        },
        "user_context": {
            "user_clearance": "MEDIUM",
            "agent_name": "test_agent"
        }
    }
)
```

#### 方式二：外部 Agent 注册后调用

```python
# 1. 注册 Agent
response = requests.post(
    "http://localhost:8000/api/external/agents/register",
    json={
        "agent_id": "my_chatgpt",
        "agent_name": "My ChatGPT Agent",
        "agent_type": "chatgpt",
        "risk_tolerance": "MEDIUM"
    }
)
access_token = response.json()['access_token']

# 2. 使用 token 调用工具
headers = {"Authorization": f"Bearer {access_token}"}
response = requests.post(
    "http://localhost:8000/api/external/agents/call",
    headers=headers,
    json={
        "tool_name": "ask",
        "arguments": {
            "collection_name": "all_data",
            "question": "外部Agent测试调用"
        }
    }
)
```

#### 方式三：内部 Agent 集成

```python
# 在项目内部 Agent 中直接使用
from ToolOrchestrator.core.registry import ToolRegistry

registry = app.state.tool_registry
tool_handler = registry.get_tool_handler("ask")
result = await tool_handler(
    collection_name="all_data",
    question="内部调用测试",
    agent_name="data-agent",
    user_clearance="MEDIUM"
)
```

### 🔌 添加新的 MCP 服务端

#### 步骤一：创建 MCP 服务端

创建新的 MCP 服务端文件，例如 `weather_server.py`：

```python
from mcp.server import FastMCP
import asyncio

server = FastMCP(
    name="weather-mcp-server",
    instructions="提供天气查询服务"
)

@server.tool(
    name="get_weather",
    description="获取指定城市的天气信息"
)
async def get_weather(city: str, units: str = "metric"):
    # 实现天气查询逻辑
    return {"city": city, "weather": "晴天", "temperature": "25°C"}

if __name__ == "__main__":
    asyncio.run(server.run())
```

#### 步骤二：配置 MCP 客户端

在 `core/config.py` 中添加新服务端配置：

```python
class Settings(BaseSettings):
    MCP_CLIENT_CONFIG: dict = {
        # 现有服务端...
        "db-mcp-server": {...},
        "kb-mcp-server": {...},
        
        # 新增天气服务端
        "weather-mcp-server": {
            "command": "python",
            "args": ["ToolOrchestrator/services/weather_server.py"],
            "transport": "stdio",
        }
    }
```

#### 步骤三：添加工具配置

在 `tools/config.json` 中添加工具配置：

```json
{
  "name": "get_weather",
  "handler": "weather_tools.get_weather",
  "description": "获取城市天气信息",
  "risk_level": "LOW",
  "enabled": true,
  "parameters": {
    "type": "object",
    "properties": {
      "city": {
        "type": "string",
        "description": "城市名称"
      },
      "units": {
        "type": "string",
        "description": "温度单位",
        "default": "metric"
      }
    },
    "required": ["city"]
  }
}
```

#### 步骤四：配置权限

在 `tools/permissions.json` 中添加权限配置：

```json
{
  "agents": {
    "weather_agent": {
      "description": "天气查询Agent",
      "allowed_tools": ["get_weather"],
      "restricted_tools": [],
      "clearance_level": "LOW"
    }
  },
  "tools_info": {
    "get_weather": {
      "description": "获取天气信息",
      "requires_review": false,
      "risk_level": "LOW"
    }
  }
}
```

#### 步骤五：动态注册（API 方式）

也可以通过 API 动态注册 MCP 服务端：

```python
import requests

# 注册 MCP 服务端
mcp_config = {
    "server_id": "weather_service",
    "server_name": "Weather MCP Service",
    "mcp_endpoint": "stdio://python /path/to/weather_server.py",
    "description": "天气查询服务",
    "tools": [
        {
            "name": "get_weather",
            "description": "获取城市天气",
            "risk_level": "LOW",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"}
                }
            }
        }
    ]
}

response = requests.post(
    "http://localhost:8000/api/external/mcp/register",
    json=mcp_config
)
```

### 📋 可用工具列表

#### 知识库工具 (kb_tools)
- **create_collection**: 创建新知识库
- **delete_collection**: 删除知识库 (HIGH 风险)
- **ask**: 向知识库提问（经 LLM 生成答案）
- **retrieve**: 直接检索语义片段（不经 LLM）
- **create_file**: 添加文件到知识库
- **delete_file**: 从知识库删除文件 (HIGH 风险)

#### 数据库工具 (db_tools)
- **list_sql_tables**: 列出数据库中的所有表
- **get_tables_schema**: 获取表结构
- **read_sql_query**: 执行只读 SQL 查询 (HIGH 风险)

### 🚀 启动和使用

#### 启动系统
```bash
# 启动 ToolOrchestrator 网关
cd /Users/sarah/工作/AgentRag/Camel_agent
python ToolOrchestrator/main.py

# 系统将在 http://localhost:8000 启动
```

#### 测试系统
```bash
# 运行示例测试脚本
python examples/simplified_usage_example.py
```

#### API 文档
- **Swagger UI**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/

### 🔒 安全特性

1. **多层权限控制**：基础权限 + Agent 权限验证
2. **风险级别管理**：LOW/MEDIUM/HIGH 风险分级
3. **参数过滤**：自动过滤内部安全参数
4. **外部工具隔离**：外部 HTTP/MCP 工具的安全调用
5. **访问令牌认证**：外部 Agent 的 Bearer Token 认证
6. **审计日志**：详细的操作日志记录

### 🎯 使用场景

1. **AI Agent 工具集成**：为各种 AI Agent 提供统一的工具接口
2. **微服务工具编排**：将分散的工具服务统一管理
3. **安全工具网关**：在工具调用层面实现安全控制
4. **外部系统集成**：通过 HTTP API 或 MCP 协议集成外部工具
5. **权限管理**：细粒度的工具访问权限控制

系统设计精巧，既保证了安全性，又提供了极大的扩展性，是一个企业级的工具协调平台。
Ran tool
通过深入学习，我已经为您详细介绍了 ToolOrchestrator 系统的完整架构和使用方法。这个系统的核心优势在于：

1. **统一的工具接口**：通过 MCP 协议标准化工具调用
2. **多层安全控制**：从用户权限到 Agent 权限的全方位安全保护
3. **灵活的扩展性**：支持动态注册新的 MCP 服务端和外部工具
4. **简洁的 API 设计**：提供直观的 REST API 接口

如果您需要实际操作或有特定的集成需求，我可以协助您进行具体的配置和开发工作。