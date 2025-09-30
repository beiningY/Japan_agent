# api/endpoints.py - 简化版工具网关API
from fastapi import APIRouter, Request, HTTPException, Header
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import json
import logging

router = APIRouter()
logger = logging.getLogger("ToolOrchestratorAPI")

# ===== 核心数据模型 =====

class ToolExecutionRequest(BaseModel):
    """工具执行请求"""
    tool_name: str
    arguments: Dict[str, Any]
    user_context: Dict[str, Any] = {"user_clearance": "LOW", "agent_name": "external_app"}

class ExternalAgentRegistration(BaseModel):
    """外部Agent注册请求"""
    agent_id: str
    agent_name: str
    agent_type: str = "external"
    risk_tolerance: str = "MEDIUM"  # LOW, MEDIUM, HIGH
    owner_email: Optional[str] = None

class ExternalToolRegistration(BaseModel):
    """外部工具注册请求"""
    name: str
    description: str
    risk_level: str = "MEDIUM"
    endpoint_url: str
    method: str = "POST"
    parameters: Optional[Dict[str, Any]] = None
    timeout: int = 30
    enabled: bool = True

class MCPServerRegistration(BaseModel):
    """MCP服务端注册请求"""
    server_id: str
    server_name: str
    mcp_endpoint: str
    tools: List[Dict[str, Any]]
    description: Optional[str] = None

# ===== 核心工具执行API =====

@router.post("/tools/execute", summary="执行工具")
async def execute_tool(request: Request, payload: ToolExecutionRequest):
    """执行已注册的工具"""
    registry = request.app.state.tool_registry
    tool_handler = registry.get_tool_handler(payload.tool_name)
    
    if not tool_handler:
        raise HTTPException(
            status_code=404, 
            detail=f"工具 '{payload.tool_name}' 未找到或已禁用"
        )
    
    # 合并参数和上下文
    combined_args = {**payload.arguments, **payload.user_context}
    
    try:
        result = await tool_handler(**combined_args)
        
        if isinstance(result, dict) and result.get("status") == "error":
            raise HTTPException(status_code=403, detail=result)
        
        return {"status": "success", "result": result}
        
    except Exception as e:
        logger.error(f"工具执行失败: {e}")
        raise HTTPException(status_code=500, detail=f"工具执行失败: {str(e)}")

@router.get("/tools", summary="列出可用工具")
async def list_tools(request: Request):
    """列出所有可用工具"""
    registry = request.app.state.tool_registry
    
    available_tools = [
        {
            "name": conf["name"],
            "description": conf.get("description", ""),
            "risk_level": conf.get("risk_level", "MEDIUM"),
            "enabled": conf.get("enabled", True)
        }
        for name, conf in registry._tools.items()
        if conf.get("enabled", True)
    ]
    
    return {
        "status": "success",
        "tools": available_tools,
        "total": len(available_tools)
    }

# ===== 外部Agent接入API =====

# 简单的内存存储（生产环境建议使用Redis）
REGISTERED_AGENTS = {}

@router.post("/external/agents/register", summary="注册外部Agent")
async def register_external_agent(registration: ExternalAgentRegistration):
    """注册外部AI Agent"""
    
    if registration.agent_id in REGISTERED_AGENTS:
        raise HTTPException(status_code=409, detail="Agent ID已存在")
    
    # 生成简单的访问token
    import hashlib
    import time
    token_data = f"{registration.agent_id}:{time.time()}"
    access_token = hashlib.md5(token_data.encode()).hexdigest()
    
    # 存储Agent信息
    REGISTERED_AGENTS[registration.agent_id] = {
        "info": registration.dict(),
        "token": access_token,
        "created_at": time.time()
    }
    
    # 自动添加到权限配置
    await add_agent_to_permissions(registration)
    
    return {
        "status": "success",
        "agent_id": registration.agent_id,
        "access_token": access_token,
        "message": "Agent注册成功"
    }

@router.post("/external/agents/call", summary="外部Agent调用工具")
async def external_agent_call_tool(
    request: Request,
    payload: ToolExecutionRequest,
    authorization: str = Header(None, description="Bearer token")
):
    """外部Agent调用工具"""
    
    # 验证token
    agent_info = verify_agent_token(authorization)
    if not agent_info:
        raise HTTPException(status_code=401, detail="无效的访问token")
    
    # 设置Agent身份
    payload.user_context.update({
        "agent_name": agent_info["agent_id"],
        "user_clearance": agent_info["risk_tolerance"]
    })
    
    # 调用工具执行
    return await execute_tool(request, payload)

@router.get("/external/agents/tools", summary="外部Agent发现工具")
async def discover_tools_for_agent(
    request: Request,
    authorization: str = Header(None, description="Bearer token")
):
    """外部Agent发现可用工具"""
    
    agent_info = verify_agent_token(authorization)
    if not agent_info:
        raise HTTPException(status_code=401, detail="无效的访问token")
    
    # 获取Agent允许的工具
    agent_tools = await get_agent_allowed_tools(agent_info["agent_id"])
    
    return {
        "status": "success",
        "agent_id": agent_info["agent_id"],
        "tools": agent_tools,
        "total": len(agent_tools)
    }

# ===== 外部工具注册API =====

@router.post("/external/tools/register", summary="注册外部工具")
async def register_external_tool(
    request: Request, 
    tool_config: ExternalToolRegistration
):
    """注册外部HTTP工具"""
    
    from ToolOrchestrator.core.config import settings
    
    # 检查工具名是否已存在
    config_path = settings.TOOLS_CONFIG_PATH
    existing_tools = load_tools_config(config_path)
    
    if any(tool.get("name") == tool_config.name for tool in existing_tools):
        raise HTTPException(status_code=409, detail="工具名已存在")
    
    # 创建工具配置
    new_tool = {
        "name": tool_config.name,
        "handler": f"external_http.{tool_config.name}",
        "description": tool_config.description,
        "risk_level": tool_config.risk_level,
        "enabled": tool_config.enabled,
        "source": "external_http",
        "endpoint_url": tool_config.endpoint_url,
        "method": tool_config.method,
        "timeout": tool_config.timeout,
        "parameters": tool_config.parameters or {}
    }
    
    # 保存配置
    existing_tools.append(new_tool)
    save_tools_config(config_path, existing_tools)
    
    # 重新加载注册器
    await reload_registry(request.app.state.tool_registry)
    
    return {
        "status": "success",
        "tool_name": tool_config.name,
        "message": "外部工具注册成功"
    }

# ===== 外部MCP服务端注册API =====

@router.post("/external/mcp/register", summary="注册MCP服务端")
async def register_mcp_server(
    request: Request,
    mcp_config: MCPServerRegistration
):
    """注册外部MCP服务端及其工具"""
    
    from ToolOrchestrator.core.config import settings
    
    config_path = settings.TOOLS_CONFIG_PATH
    existing_tools = load_tools_config(config_path)
    
    # 检查服务端ID是否已存在
    if any(tool.get("server_id") == mcp_config.server_id for tool in existing_tools):
        raise HTTPException(status_code=409, detail="MCP服务端ID已存在")
    
    registered_tools = []
    
    # 为每个工具创建配置
    for tool in mcp_config.tools:
        tool_name = f"{mcp_config.server_id}_{tool['name']}"
        
        tool_config = {
            "name": tool_name,
            "handler": f"mcp.{mcp_config.server_id}.{tool['name']}",
            "description": tool.get("description", ""),
            "risk_level": tool.get("risk_level", "MEDIUM"),
            "enabled": True,
            "source": "external_mcp",
            "server_id": mcp_config.server_id,
            "server_name": mcp_config.server_name,
            "mcp_endpoint": mcp_config.mcp_endpoint,
            "parameters": tool.get("parameters", {})
        }
        
        existing_tools.append(tool_config)
        registered_tools.append(tool_name)
    
    # 保存配置
    save_tools_config(config_path, existing_tools)
    
    # 重新加载注册器
    await reload_registry(request.app.state.tool_registry)
    
    return {
        "status": "success",
        "server_id": mcp_config.server_id,
        "registered_tools": registered_tools,
        "total": len(registered_tools),
        "message": "MCP服务端注册成功"
    }

@router.get("/external/mcp/servers", summary="列出MCP服务端")
async def list_mcp_servers():
    """列出已注册的MCP服务端"""
    
    from ToolOrchestrator.core.config import settings
    
    existing_tools = load_tools_config(settings.TOOLS_CONFIG_PATH)
    
    # 按服务端分组
    servers = {}
    for tool in existing_tools:
        if tool.get("source") == "external_mcp":
            server_id = tool.get("server_id")
            if server_id not in servers:
                servers[server_id] = {
                    "server_id": server_id,
                    "server_name": tool.get("server_name", server_id),
                    "tools": [],
                    "total_tools": 0
                }
            servers[server_id]["tools"].append(tool["name"])
            servers[server_id]["total_tools"] += 1
    
    return {
        "status": "success",
        "servers": list(servers.values()),
        "total": len(servers)
    }

# ===== 辅助函数 =====

def verify_agent_token(authorization: str) -> Optional[Dict]:
    """验证Agent访问token"""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    token = authorization.split(" ")[1]
    
    for agent_id, agent_data in REGISTERED_AGENTS.items():
        if agent_data["token"] == token:
            return {"agent_id": agent_id, **agent_data["info"]}
    
    return None

async def add_agent_to_permissions(registration: ExternalAgentRegistration):
    """添加Agent到权限配置"""
    permissions_file = "tools/permissions.json"
    
    try:
        with open(permissions_file, "r", encoding="utf-8") as f:
            permissions = json.load(f)
    except FileNotFoundError:
        permissions = {"agents": {}, "tools_info": {}}
    
    # 根据风险容忍度设置默认工具
    default_tools = []
    if registration.risk_tolerance == "LOW":
        default_tools = ["ask", "retrieve"]
    elif registration.risk_tolerance == "MEDIUM":
        default_tools = ["ask", "retrieve", "list_sql_tables", "get_tables_schema"]
    elif registration.risk_tolerance == "HIGH":
        default_tools = ["ask", "retrieve", "list_sql_tables", "get_tables_schema", "read_sql_query"]
    
    # 添加Agent配置
    permissions["agents"][registration.agent_id] = {
        "description": f"外部{registration.agent_type} Agent - {registration.agent_name}",
        "allowed_tools": default_tools,
        "restricted_tools": [],
        "clearance_level": registration.risk_tolerance,
        "agent_type": "external"
    }
    
    # 保存配置
    with open(permissions_file, "w", encoding="utf-8") as f:
        json.dump(permissions, f, ensure_ascii=False, indent=2)

async def get_agent_allowed_tools(agent_id: str) -> List[Dict]:
    """获取Agent允许使用的工具列表"""
    try:
        with open("tools/permissions.json", "r", encoding="utf-8") as f:
            permissions = json.load(f)
        
        agent_perms = permissions.get("agents", {}).get(agent_id, {})
        allowed_tools = agent_perms.get("allowed_tools", [])
        
        # 构建工具详情
        tools_info = []
        for tool_name in allowed_tools:
            tools_info.append({
                "name": tool_name,
                "description": f"工具: {tool_name}",
                "risk_level": "MEDIUM"
            })
        
        return tools_info
        
    except Exception as e:
        logger.error(f"获取Agent工具列表失败: {e}")
        return []

def load_tools_config(config_path: str) -> List[Dict]:
    """加载工具配置"""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_tools_config(config_path: str, tools: List[Dict]):
    """保存工具配置"""
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(tools, f, ensure_ascii=False, indent=2)

async def reload_registry(registry):
    """重新加载工具注册器"""
    from ToolOrchestrator.core.config import settings
    
    registry._tools.clear()
    registry.load_from_json(settings.TOOLS_CONFIG_PATH)
    logger.info("工具注册器已重新加载")

# ===== 删除工具API =====

@router.delete("/tools/{tool_name}", summary="删除工具")
async def delete_tool(request: Request, tool_name: str):
    """删除指定工具"""
    from ToolOrchestrator.core.config import settings
    
    config_path = settings.TOOLS_CONFIG_PATH
    existing_tools = load_tools_config(config_path)
    
    # 查找并移除工具
    updated_tools = [tool for tool in existing_tools if tool.get("name") != tool_name]
    
    if len(updated_tools) == len(existing_tools):
        raise HTTPException(status_code=404, detail="工具未找到")
    
    # 保存配置
    save_tools_config(config_path, updated_tools)
    
    # 重新加载注册器
    await reload_registry(request.app.state.tool_registry)
    
    return {
        "status": "success",
        "message": f"工具 '{tool_name}' 已删除"
    }

@router.delete("/external/mcp/{server_id}", summary="删除MCP服务端")
async def delete_mcp_server(request: Request, server_id: str):
    """删除MCP服务端及其所有工具"""
    from ToolOrchestrator.core.config import settings
    
    config_path = settings.TOOLS_CONFIG_PATH
    existing_tools = load_tools_config(config_path)
    
    # 找到该服务端的工具
    server_tools = [tool["name"] for tool in existing_tools if tool.get("server_id") == server_id]
    
    if not server_tools:
        raise HTTPException(status_code=404, detail="MCP服务端未找到")
    
    # 移除该服务端的所有工具
    updated_tools = [tool for tool in existing_tools if tool.get("server_id") != server_id]
    
    # 保存配置
    save_tools_config(config_path, updated_tools)
    
    # 重新加载注册器
    await reload_registry(request.app.state.tool_registry)
    
    return {
        "status": "success",
        "message": f"MCP服务端 '{server_id}' 及其 {len(server_tools)} 个工具已删除",
        "removed_tools": server_tools
    }