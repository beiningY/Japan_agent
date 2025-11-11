import asyncio
import json
import logging
import os
import aiohttp
from typing import Dict, List, Any
from langchain_core.tools import BaseTool

logger = logging.getLogger("MultiServerMCPClient")


class MCPTool(BaseTool):
    """简化的工具占位，符合 ToolRegistry 下游工具接口。"""
    def __init__(self, name: str, description: str):
        super().__init__(name=name, description=description)

    async def _arun(self, *args, **kwargs) -> Any:
        raise NotImplementedError("Use MultiServerMCPClient.invoke instead.")

    def _run(self, *args, **kwargs) -> Any:
        raise NotImplementedError("Use MultiServerMCPClient.invoke instead.")


class MultiServerMCPClient:
    """
    最简实现：
    - 从 tools/config.json 读取工具列表作为“发现的工具”。
    - invoke() 直接调用本地的 kb_tools/db_tools 函数（绕过 FastMCP 进程与协议）。
    这样即可与现有 ToolRegistry 兼容，无需启动子进程。
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tools: Dict[str, MCPTool] = {}

        # 延迟导入，避免无用依赖
        from ToolOrchestrator.core.config import settings  # type: ignore
        self._tools_config_path = settings.TOOLS_CONFIG_PATH

        # 本地函数映射
        from ToolOrchestrator.tools import kb_tools, db_tools, web_search_tools  # type: ignore
        self._kb = kb_tools
        self._db = db_tools
        self._web_search = web_search_tools

    async def get_tools(self) -> List[BaseTool]:
        try:
            with open(self._tools_config_path, "r", encoding="utf-8") as f:
                cfg_list = json.load(f)
        except Exception as e:
            logger.error(f"读取工具配置失败: {e}")
            cfg_list = []

        discovered: Dict[str, MCPTool] = {}
        for item in cfg_list:
            if not item.get("enabled", False):
                continue
            name = item.get("name")
            desc = item.get("description", name)
            if name:
                discovered[name] = MCPTool(name, desc)

        self.tools = discovered
        logger.info(f"Discovered local tools: {list(self.tools.keys())}")
        return list(discovered.values())

    async def invoke(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name not in self.tools:
            return {"status": "error", "reason": f"Tool not found: {tool_name}"}

        # 检查是否是外部HTTP工具
        tool_config = self._get_tool_config(tool_name)
        if tool_config and tool_config.get("source") == "external_http":
            return await self._invoke_external_http_tool(tool_name, args, tool_config)

        # 统一适配参数并调用本地实现
        try:
            if tool_name == "create_collection":
                return {"status": "ok", "result": self._kb.create(args.get("collection_name"))}
            if tool_name == "delete_collection":
                return {"status": "ok", "result": self._kb.delete(args.get("collection_name"))}
            if tool_name == "create_file":
                return {"status": "ok", "result": self._kb.add_file(args.get("file_path"), args.get("collection_name"))}
            if tool_name == "delete_file":
                return {"status": "ok", "result": self._kb.deletefile(args.get("file_path"), args.get("collection_name"))}
            if tool_name == "ask":
                return {"status": "ok", "result": self._kb.ask(args.get("question"), kb_name=args.get("collection_name"))}
            if tool_name == "retrieve":
                return {"status": "ok", "result": self._kb.retrieve(args.get("collection_name"), args.get("question"), args.get("k", 5))}

            # DB 工具为异步函数，使用事件循环运行
            async def _db_call(coro):
                return await coro

            if tool_name == "list_sql_tables":
                return {"status": "ok", "result": await _db_call(self._db.list_sql_tables())}
            if tool_name == "get_tables_schema":
                return {"status": "ok", "result": await _db_call(self._db.get_tables_schema(args.get("table_names", [])))}
            if tool_name == "read_sql_query":
                return {"status": "ok", "result": await _db_call(self._db.read_sql_query(args.get("table_queries", [])))}
            if tool_name == "read_query_for_sensor_readings":
                return {"status": "ok", "result": await _db_call(self._db.read_query_for_sensor_readings(args.get("table_queries", [])))}

            # 联网搜索工具
            if tool_name == "web_search":
                return {"status": "ok", "result": self._web_search.web_search(
                    args.get("query"), 
                    args.get("max_results", 3),
                    args.get("search_depth", "basic")
                )}

            return {"status": "error", "reason": f"Unknown tool: {tool_name}"}
        except Exception as e:
            logger.error(f"Local tool invoke error: {e}")
            return {"status": "error", "reason": str(e)}

    def _get_tool_config(self, tool_name: str) -> Dict[str, Any]:
        """获取工具的完整配置信息"""
        try:
            with open(self._tools_config_path, "r", encoding="utf-8") as f:
                cfg_list = json.load(f)
                
            for item in cfg_list:
                if item.get("name") == tool_name:
                    return item
            return {}
        except Exception as e:
            logger.error(f"读取工具配置失败: {e}")
            return {}

    async def _invoke_external_http_tool(self, tool_name: str, args: Dict[str, Any], tool_config: Dict[str, Any]) -> Dict[str, Any]:
        """调用外部HTTP工具"""
        endpoint_url = tool_config.get("endpoint_url")
        method = tool_config.get("method", "POST").upper()
        headers = tool_config.get("headers", {})
        timeout = tool_config.get("timeout", 30)
        
        if not endpoint_url:
            return {"status": "error", "reason": f"No endpoint_url configured for tool {tool_name}"}
        
        # 准备请求数据
        request_data = {
            "tool_name": tool_name,
            "arguments": args,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        # 设置默认的Content-Type
        if "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                if method == "POST":
                    async with session.post(endpoint_url, json=request_data, headers=headers) as response:
                        return await self._handle_http_response(response, tool_name)
                elif method == "PUT":
                    async with session.put(endpoint_url, json=request_data, headers=headers) as response:
                        return await self._handle_http_response(response, tool_name)
                elif method == "GET":
                    # GET请求将参数放在查询字符串中
                    params = {"tool_data": json.dumps(request_data)}
                    async with session.get(endpoint_url, params=params, headers=headers) as response:
                        return await self._handle_http_response(response, tool_name)
                else:
                    return {"status": "error", "reason": f"Unsupported HTTP method: {method}"}
                    
        except asyncio.TimeoutError:
            logger.error(f"HTTP request timeout for tool {tool_name}")
            return {"status": "error", "reason": f"Request timeout for tool {tool_name}"}
        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error for tool {tool_name}: {e}")
            return {"status": "error", "reason": f"HTTP client error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error calling external tool {tool_name}: {e}")
            return {"status": "error", "reason": f"Unexpected error: {str(e)}"}

    async def _handle_http_response(self, response: aiohttp.ClientResponse, tool_name: str) -> Dict[str, Any]:
        """处理HTTP响应"""
        try:
            if response.status == 200:
                response_data = await response.json()
                return response_data
            else:
                error_text = await response.text()
                logger.error(f"HTTP {response.status} error for tool {tool_name}: {error_text}")
                return {
                    "status": "error", 
                    "reason": f"HTTP {response.status}: {error_text}"
                }
        except json.JSONDecodeError:
            error_text = await response.text()
            logger.error(f"Invalid JSON response from tool {tool_name}: {error_text}")
            return {
                "status": "error",
                "reason": f"Invalid JSON response: {error_text}"
            }

    async def close(self):
        # 无子进程可关闭，直接返回
        self.tools.clear()
