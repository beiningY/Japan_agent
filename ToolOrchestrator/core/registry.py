# core/registry.py
"""
工具注册表 - 集中安全审查的核心组件
"""

import json
import functools
import logging
from typing import Callable, Dict, Any

from .security import security_validator, SecurityResult
from ToolOrchestrator.client.client import MultiServerMCPClient

logger = logging.getLogger("ToolRegistry")


class ToolRegistry:
    """工具注册表 - 集中处理安全审查"""

    def __init__(self, mcp_client_config: dict):
        self._tools: Dict[str, dict] = {}
        self.mcp_client = MultiServerMCPClient(mcp_client_config)
        self.downstream_tools = []

    async def initialize_connections(self):
        """初始化MCP连接"""
        self.downstream_tools = await self.mcp_client.get_tools()
        logger.info(f"获取到 {len(self.downstream_tools)} 个工具")

    def _create_secure_handler(self, tool_name: str) -> Callable:
        """创建带安全检查的工具处理器"""

        @functools.wraps(self._create_mcp_handler(tool_name))
        async def secure_handler(*args, **kwargs):
            # 提取安全相关参数
            agent_name = kwargs.get("agent_name", "unknown_agent")
            user_clearance = kwargs.get("user_clearance", "LOW")

            # 统一安全检查
            security_result = security_validator.validate_agent_tool_access(
                agent_name=agent_name,
                tool_name=tool_name,
                user_clearance=user_clearance
            )

            if not security_result.allowed:
                logger.warning(f"安全检查失败: {security_result.reason}")
                return {
                    "status": "error",
                    "reason": security_result.reason,
                    "risk_level": security_result.risk_level
                }

            # 特定工具的安全验证
            if tool_name == "read_sql_query":
                queries = kwargs.get("table_queries", [])
                for query_obj in queries:
                    if isinstance(query_obj, dict) and "query" in query_obj:
                        sql_result = security_validator.validate_sql_query(query_obj["query"])
                        if not sql_result.allowed:
                            return {"status": "error", "reason": f"SQL安全检查失败: {sql_result.reason}"}

            elif tool_name in ["create_file", "delete_file"]:
                file_path = kwargs.get("file_path", "")
                file_result = security_validator.validate_file_path(file_path)
                if not file_result.allowed:
                    return {"status": "error", "reason": f"文件路径检查失败: {file_result.reason}"}

            logger.info(f"安全检查通过: {agent_name} 使用工具 {tool_name}")

            # 清理内部参数
            clean_kwargs = self._clean_internal_params(kwargs)

            # 调用实际工具
            try:
                return await self._create_mcp_handler(tool_name)(**clean_kwargs)
            except Exception as e:
                logger.error(f"工具 {tool_name} 执行失败: {e}")
                return {"status": "error", "reason": f"工具执行失败: {str(e)}"}

        return secure_handler

    def _create_mcp_handler(self, tool_name: str) -> Callable:
        """创建MCP工具处理器"""
        async def mcp_handler(*args, **kwargs):
            return await self.mcp_client.invoke(tool_name, kwargs)
        return mcp_handler

    def _clean_internal_params(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """清理内部参数"""
        internal_params = {
            'user_clearance', 'user_id', 'user_context',
            'agent_name', 'action', 'query', 'user_query'
        }
        return {k: v for k, v in kwargs.items() if k not in internal_params}

    def load_from_json(self, json_file: str):
        """从JSON配置加载工具"""
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                tools_config = json.load(f)
        except Exception as e:
            logger.error(f"加载工具配置失败: {e}")
            return

        for config in tools_config:
            name = config["name"]

            # 检查工具是否在下游服务中存在
            if not any(t.name == name for t in self.downstream_tools):
                logger.warning(f"工具 {name} 未在MCP服务中找到，跳过")
                continue

            if not config.get("enabled", False):
                logger.info(f"工具 {name} 已禁用，跳过")
                continue

            # 创建安全包装的处理器
            secure_handler = self._create_secure_handler(name)

            # 保存工具配置
            tool_config = dict(config)
            tool_config["handler"] = secure_handler
            self._tools[name] = tool_config

            logger.info(f"工具 {name} 注册成功")

    def get_tool_handler(self, name: str) -> Callable:
        """获取工具处理器"""
        tool = self._tools.get(name)
        return tool["handler"] if tool else None

    def get_tool_config(self, name: str) -> dict:
        """获取工具配置"""
        return self._tools.get(name)

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """调用已注册工具（带安全包装的处理器）"""
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"未注册的工具: {name}")
        handler = tool.get("handler")
        if not handler:
            raise RuntimeError(f"工具 {name} 未初始化处理器")
        return await handler(**arguments)