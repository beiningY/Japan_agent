"""
MCP 安全网关
负责基于 JSON 策略与角色权限，对 MCP 工具进行列出与调用前的集中校验。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from ..tools.permission_manager import permission_manager


logger = logging.getLogger("mcp_security_gateway")


class MCPSecurityGateway:
    def __init__(self, username: str) -> None:
        self.username = username

    def filter_tools(self, tools: List[Any]) -> List[Any]:
        return permission_manager.filter_mcp_tools_for_user(self.username, tools)

    def check_invocation(
        self, tool_name: str, params: Dict[str, Any] | None, *, approved: bool = False
    ) -> Tuple[bool, str]:
        return permission_manager.check_mcp_tool_access(
            self.username, tool_name, params or {}, approved=approved
        )


