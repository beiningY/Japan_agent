import json
import functools
import logging
import sys
import os
from typing import Callable, Dict, List, Any
from ToolOrchestrator.client.client import MultiServerMCPClient, BaseTool

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from agents.security_agent import SecurityReviewAgent
except ImportError:
    logger = logging.getLogger("ToolRegistry")
    logger.warning("无法导入SecurityReviewAgent，将跳过智能安全审查")
    SecurityReviewAgent = None


logger = logging.getLogger("ToolRegistry")

# 定义 ToolRegistry类，工具网关的核心，用来发现、配置、保护和调度所有的下游工具
class ToolRegistry:
    def __init__(self, mcp_client_config: dict):
        # 用于储存所有最终被完全配置和包装好的工具 str工具名 dict所有工具的信息
        self._tools: Dict[str, dict] = {}
        # 创建一个MultiServerMCPClient实例，用于与所有MCP服务端通信
        self.mcp_client = MultiServerMCPClient(mcp_client_config)
        # 用于储存所有被发现的工具
        self.downstream_tools: List[BaseTool] = []
        # 初始化SecurityReviewAgent
        try:
            self.security_agent = SecurityReviewAgent() if SecurityReviewAgent else None
        except Exception as e:
            logger.warning(f"初始化SecurityReviewAgent失败: {e}")
            self.security_agent = None


    # 用于连接到所有下游服务并获取它们提供的工具列表。这个方法必须在服务启动时、加载配置之前调用。
    async def initialize_connections(self):
        self.downstream_tools = await self.mcp_client.get_tools()
        logger.info(f"成功获取 {len(self.downstream_tools)} 个工具来自下所有下游MCP服务端。")
    
    # 定义一个动态装饰器 他接收一个工具名和一个处理方法 返回一个被包装后的新函数
    def _security_wrapper(self, tool_name: str, original_handler: Callable) -> Callable:
        # 使用functools.wraps来复制原始处理方法的元数据
        @functools.wraps(original_handler)
        # 定义包装函数 `wrapper`。它接受任意数量的位置参数 (*args) 和关键字参数 (**kwargs)。因为工具的参数未知
        async def wrapper(*args, **kwargs):
            # 获取工具的配置信息
            tool_info = self.get_tool_config(tool_name)
            if not tool_info:
                 return {"status": "error", "reason": f"工具 '{tool_name}' 的信息权限未再网关配置中。"}
            
            # Layer 1: 基础权限检查 (ToolOrchestrator层)
            risk_level = tool_info.get("risk_level", "LOW")
            user_clearance = kwargs.get("user_clearance", "LOW")
            
            clearance_map = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
            if clearance_map.get(user_clearance.upper(), 0) < clearance_map.get(risk_level.upper(), 0):
                reason = f"执行拒绝: 用户权限 '{user_clearance}' 不足以执行风险等级 '{risk_level}' 的工具 '{tool_name}'."
                logger.warning(reason)
                return {"status": "error", "reason": reason}
            
            # Layer 2: SecurityReviewAgent智能安全审查
            if self.security_agent:
                try:
                    # 从kwargs中提取必要参数
                    agent_name = kwargs.get("agent_name", "UnknownAgent")
                    action = kwargs.get("action", f"调用工具 {tool_name}")
                    query = kwargs.get("query", kwargs.get("user_query", ""))
                    
                    # 进行安全审查
                    security_result = self.security_agent.check_tool_call(
                        agent_name, tool_name, action, query
                    )
                    
                    # 处理安全审查结果
                    if security_result.get("decision") == "DENY":
                        reason = f"安全审查拒绝: {security_result.get('reason', '未知原因')}"
                        logger.warning(reason)
                        return {"status": "error", "reason": reason}
                    
                    if security_result.get("decision") == "REVIEW":
                        logger.warning(f"工具 {tool_name} 需要人工审查: {security_result.get('reason')}")
                        # 在实际项目中，这里应该触发人工审查流程
                        # 暂时记录日志但允许执行
                    
                    logger.info(f"安全审查通过: {agent_name} 使用 {tool_name}")
                    
                except Exception as e:
                    logger.error(f"SecurityReviewAgent检查出错: {e}")
                    # 可以选择在安全检查出错时拒绝执行，或者继续执行
                    # 这里选择继续执行但记录错误
                    logger.warning("安全检查出错，继续执行但需要人工审查")
            else:
                logger.debug("SecurityReviewAgent未初始化，跳过智能安全审查")
            
            logger.info(f"权限检查通过，继续调用MCP '{tool_name}'.")
            return await original_handler(*args, **kwargs)
        return wrapper

    def _create_mcp_handler(self, tool_name: str) -> Callable:
        async def mcp_handler(*args, **kwargs):
            # 内部参数，不需要传递给MCP服务端
            internal_args = ['user_clearance', 'user_id', 'user_context', 'agent_name', 'action', 'query', 'user_query']
            # 过滤掉内部参数，只传递给MCP服务端的参数
            tool_args = {k: v for k, v in kwargs.items() if k not in internal_args}
            
            try:
                # 调用mcp_client的invoke方法，传递工具名和参数
                result = await self.mcp_client.invoke(tool_name, tool_args)
                return result
            except Exception as e:
                logger.error(f"MCP调用工具 '{tool_name}' 失败: {e}", exc_info=True)
                return {"status": "error", "reason": f"工具 '{tool_name}' 执行失败."}
        return mcp_handler

    def load_from_json(self, json_file: str):
        with open(json_file, "r", encoding="utf-8") as f:
            tools_config_list = json.load(f)

        for config in tools_config_list:
            name = config["name"]
            if not any(t.name == name for t in self.downstream_tools):
                logger.warning(f"配置中的工具 '{name}' 未在发现的MCP服务端中找到. 跳过.")
                continue
            
            if not config.get("enabled", False):
                logger.info(f"配置中的工具 '{name}' 被禁用. 跳过.")
                continue

            original_handler = self._create_mcp_handler(name)
            wrapped_handler = self._security_wrapper(name, original_handler)
            
            self._tools[name] = {"name": name, "handler": wrapped_handler, **config}
            logger.info(f"成功注册和包装MCP工具: {name}")

    def get_tool_handler(self, name: str) -> Callable | None:
        # 获取工具的处理器
        tool = self._tools.get(name)
        return tool["handler"] if tool else None

    def get_tool_config(self, name: str) -> dict | None:
        # 获取工具的配置信息
        return self._tools.get(name)