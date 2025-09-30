"""
全局工具管理器
用于在服务启动时集中管理所有MCP工具的注册，避免每次请求时重复初始化。
"""

import logging
import asyncio
from typing import Optional
from ToolOrchestrator.core.registry import ToolRegistry
from ToolOrchestrator.core.config import settings

logger = logging.getLogger("GlobalToolManager")

class GlobalToolManager:
    """全局工具管理器，单例模式管理ToolRegistry实例"""
    
    _instance: Optional['GlobalToolManager'] = None
    _registry: Optional[ToolRegistry] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @property
    def registry(self) -> Optional[ToolRegistry]:
        """获取已初始化的ToolRegistry实例"""
        return self._registry
    
    @property
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized
    
    async def initialize(self) -> bool:
        """初始化全局工具注册器
        
        Returns:
            bool: 初始化是否成功
        """
        if self._initialized:
            logger.info("全局工具管理器已初始化，跳过重复初始化")
            return True
            
        try:
            logger.info("开始初始化全局MCP工具注册器...")
            
            # 创建ToolRegistry实例
            self._registry = ToolRegistry(mcp_client_config=settings.MCP_CLIENT_CONFIG)
            
            # 初始化连接和加载工具配置
            await self._registry.initialize_connections()
            self._registry.load_from_json(settings.TOOLS_CONFIG_PATH)
            
            self._initialized = True
            logger.info(f"全局MCP工具注册器初始化完成！已注册 {len(self._registry._tools)} 个工具")
            
            # 打印已注册的工具列表
            if self._registry._tools:
                tool_list = list(self._registry._tools.keys())
                logger.info(f"已注册的工具: {', '.join(tool_list)}")
            
            return True
            
        except Exception as e:
            logger.error(f"全局工具注册器初始化失败: {e}", exc_info=True)
            self._registry = None
            self._initialized = False
            return False
    
    def get_tool_handler(self, tool_name: str):
        """获取工具处理器
        
        Args:
            tool_name: 工具名称
            
        Returns:
            工具处理器函数，如果工具不存在则返回None
        """
        if not self._registry:
            logger.error("工具注册器未初始化，无法获取工具处理器")
            return None
            
        return self._registry.get_tool_handler(tool_name)
    
    def get_tool_config(self, tool_name: str):
        """获取工具配置信息
        
        Args:
            tool_name: 工具名称
            
        Returns:
            工具配置字典，如果工具不存在则返回None
        """
        if not self._registry:
            logger.error("工具注册器未初始化，无法获取工具配置")
            return None
            
        return self._registry.get_tool_config(tool_name)
    
    def list_available_tools(self) -> list:
        """列出所有可用工具
        
        Returns:
            工具名称列表
        """
        if not self._registry:
            logger.error("工具注册器未初始化，无法列出工具")
            return []
            
        return list(self._registry._tools.keys())


# 全局实例
global_tool_manager = GlobalToolManager()


def initialize_global_tools():
    """同步方式初始化全局工具（用于非异步环境）"""
    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(global_tool_manager.initialize())
    except RuntimeError:
        # 如果没有运行中的事件循环，创建一个新的
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(global_tool_manager.initialize())
        finally:
            loop.close()


async def async_initialize_global_tools():
    """异步方式初始化全局工具"""
    return await global_tool_manager.initialize()
