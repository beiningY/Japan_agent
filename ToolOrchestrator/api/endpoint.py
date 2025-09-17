# api/endpoints.py
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

router = APIRouter()

class ToolExecutionRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    user_context: Dict[str, Any] = {"user_clearance": "LOW"}

@router.post("/tools/execute", summary="执行一个注册的工具")
async def execute_tool(request: Request, payload: ToolExecutionRequest):
    registry = request.app.state.tool_registry
    tool_handler = registry.get_tool_handler(payload.tool_name)
    
    if not tool_handler:
        raise HTTPException(status_code=404, detail=f"Tool '{payload.tool_name}' not found or is disabled.")
        
    combined_args = {**payload.arguments, **payload.user_context}
    
    result = await tool_handler(**combined_args)
    
    if isinstance(result, dict) and result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result)
        
    return result

@router.get("/tools", summary="列出所有可用的工具")
async def list_tools(request: Request):
    """Lists all tools that are enabled and available through the gateway."""
    registry = request.app.state.tool_registry
    # 只返回工具的非敏感配置信息
    available_tools = [
        {"name": conf["name"], "risk_level": conf["risk_level"]}
        for name, conf in registry._tools.items()
    ]
    return available_tools