# langchain_mcp_adapters/client.py
import asyncio
import json
import logging
from typing import Dict, List, Any
from langchain_core.tools import BaseTool

logger = logging.getLogger("MultiServerMCPClient")


class MCPTool(BaseTool):
    """简单的 MCP 工具封装"""
    def __init__(self, name: str, description: str, server_name: str):
        super().__init__(name=name, description=description)
        self.server_name = server_name

    async def _arun(self, *args, **kwargs) -> Any:
        raise NotImplementedError("Use MultiServerMCPClient.invoke instead.")

    def _run(self, *args, **kwargs) -> Any:
        raise NotImplementedError("Use MultiServerMCPClient.invoke instead.")


class MultiServerMCPClient:
    def __init__(self, config: Dict[str, Any]):
        """
        config 示例:
        {
            "db-mcp-server": {
                "command": "python",
                "args": ["services/db_server.py"],
                "transport": "stdio",
            },
            "kb-mcp-server": {
                "command": "python",
                "args": ["services/kb_server.py"],
                "transport": "stdio",
            }
        }
        """
        self.config = config
        self.processes: Dict[str, asyncio.subprocess.Process] = {}
        self.tools: Dict[str, MCPTool] = {}

    async def _start_server(self, name: str, cfg: dict):
        """启动 MCP 子进程"""
        if cfg["transport"] != "stdio":
            raise NotImplementedError("Only stdio transport is implemented.")

        process = await asyncio.create_subprocess_exec(
            cfg["command"], *cfg["args"],
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self.processes[name] = process
        logger.info(f"Started MCP server '{name}' (PID={process.pid})")

        return process

    async def get_tools(self) -> List[BaseTool]:
        """从所有 MCP 服务发现工具"""
        discovered_tools: Dict[str, MCPTool] = {}

        for name, cfg in self.config.items():
            process = self.processes.get(name)
            if not process:
                process = await self._start_server(name, cfg)

            try:
                # 假设约定: 向子进程发送 {"command": "list_tools"}
                request = {"command": "list_tools"}
                process.stdin.write((json.dumps(request) + "\n").encode())
                await process.stdin.drain()

                line = await process.stdout.readline()
                if not line:
                    raise RuntimeError("No response from MCP server")

                data = json.loads(line.decode())
                for tool in data.get("tools", []):
                    tool_name = tool["name"]
                    desc = tool.get("description", "")
                    discovered_tools[tool_name] = MCPTool(tool_name, desc, name)

                logger.info(f"Discovered tools from '{name}': {list(discovered_tools.keys())}")
            except Exception as e:
                logger.error(f"Failed to get tools from '{name}': {e}", exc_info=True)

        self.tools = discovered_tools
        return list(discovered_tools.values())

    async def invoke(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """调用指定工具"""
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not found in MCP registry.")

        server_name = self.tools[tool_name].server_name
        process = self.processes[server_name]

        try:
            request = {"command": "invoke", "tool": tool_name, "args": args}
            process.stdin.write((json.dumps(request) + "\n").encode())
            await process.stdin.drain()

            line = await process.stdout.readline()
            if not line:
                raise RuntimeError("No response from MCP server")

            return json.loads(line.decode())
        except Exception as e:
            logger.error(f"Failed to invoke '{tool_name}' on server '{server_name}': {e}", exc_info=True)
            return {"status": "error", "reason": str(e)}

    async def close(self):
        """关闭所有子进程"""
        for name, process in self.processes.items():
            if process.returncode is None:
                process.terminate()
                await process.wait()
                logger.info(f"Terminated MCP server '{name}'")
        self.processes.clear()
