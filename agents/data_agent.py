from __future__ import annotations
from typing import Any, Dict, List, Optional
from .mcp_toolcall_agent import MCPToolCallAgent
from utils.logger import get_logger
logger = get_logger(__name__)

class DataAgent(MCPToolCallAgent):
    """面向数据分析（知识库 + 数据库）的 ToolCall 智能体。

    - 继承 MCPToolCallAgent：沿用 OpenAI tools 决策 + MCP 执行
    - 约束工具集合：仅暴露 KB / DB 相关工具
    - 默认系统提示：规范回答格式与使用工具策略
    """

    name: str = "data-agent"
    description: Optional[str] = "Analyze KB and DB via MCP toolcalls"

    def __init__(self, *, system_prompt: Optional[str] = None, **kwargs) -> None:
        default_system = (
            "你是数据获取与分析助手。请使用工具获取知识库与数据库的真实数据；然后根据真实的数据来回答用户的问题。"
            "你可以使用 retrieve 工具从知识库检索南美白对虾养殖的专业知识，"
            "若查询数据库则需要首先根据需求使用list_sql_tables，get_tables_schema对于数据库的表进行了解，"
            "然后再调用执行查询命令的工具read_sql_query。最后根据检索到的真实数据来回答用户的问题。"
            "不要直接使用你自己的知识回答，必须基于工具返回的数据。回答中请明确引用来源（表名/文件名），并避免臆断。"
            "传感器数据类型sensor_types表, sensor_readings表里是最新的数据。"
            "对于retriever工具如果检索到相关信息了则不重复检索，尽量针对相同的问题只进行单次的检索。"
        )
        super().__init__(system_prompt=system_prompt or default_system, **kwargs)

    async def _ensure_tools_ready(self):
        # 使用父类加载所有工具后，筛选只保留 KB/DB 工具
        await super()._ensure_tools_ready()
        assert self._tools_param_cache is not None

        allowed_prefixes = { "retrieve","list_sql_tables", "get_tables_schema", "read_sql_query"}
        filtered_tools: List[Dict[str, Any]] = []
        for t in self._tools_param_cache:
            fn = t.get("function", {})
            name = fn.get("name")
            if name in allowed_prefixes:
                filtered_tools.append(t)
        self._tools_param_cache = filtered_tools


