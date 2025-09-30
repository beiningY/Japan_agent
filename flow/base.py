# flow/base.py
"""
BaseFlow - 流程基础类

定义多智能体协作流程的基础接口和通用功能
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union, Any
import logging

from agents.core_schema import AgentState

logger = logging.getLogger(__name__)


@dataclass
class BaseAgent:
    """Agent基础接口，适配不同类型的智能体"""
    name: str
    description: str = ""
    state: AgentState = AgentState.IDLE

    async def run(self, prompt: str) -> str:
        """执行任务的统一接口"""
        raise NotImplementedError("子类必须实现run方法")

    async def cleanup(self) -> None:
        """清理资源"""
        pass


@dataclass
class CamelAgent(BaseAgent):
    """Camel项目的Agent包装器"""
    agent_instance: Any = None

    async def run(self, prompt: str) -> str:
        """调用实际的agent实例"""
        if self.agent_instance and hasattr(self.agent_instance, 'run'):
            self.state = AgentState.RUNNING
            try:
                result = await self.agent_instance.run(prompt)
                self.state = AgentState.FINISHED
                return result
            except Exception as e:
                self.state = AgentState.ERROR
                logger.error(f"Agent {self.name} 执行失败: {e}")
                raise
        else:
            raise RuntimeError(f"Agent {self.name} 未正确初始化")

    async def cleanup(self) -> None:
        """清理agent资源"""
        if self.agent_instance and hasattr(self.agent_instance, 'cleanup'):
            await self.agent_instance.cleanup()


@dataclass
class BaseFlow(ABC):
    """流程基础类 - 支持多智能体协作"""

    agents: Dict[str, BaseAgent] = field(default_factory=dict)
    primary_agent_key: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化后处理"""
        # 如果没有指定主agent，使用第一个
        if not self.primary_agent_key and self.agents:
            self.primary_agent_key = next(iter(self.agents))

    @property
    def primary_agent(self) -> Optional[BaseAgent]:
        """获取主要执行agent"""
        if self.primary_agent_key:
            return self.agents.get(self.primary_agent_key)
        return None

    def get_agent(self, key: str) -> Optional[BaseAgent]:
        """根据key获取特定agent"""
        return self.agents.get(key)

    def add_agent(self, key: str, agent: BaseAgent) -> None:
        """添加新的agent"""
        self.agents[key] = agent
        # 如果这是第一个agent，设为主agent
        if not self.primary_agent_key:
            self.primary_agent_key = key

    def get_executor(self, step_type: Optional[str] = None) -> Optional[BaseAgent]:
        """
        根据步骤类型选择合适的执行器
        子类可以重写此方法来实现更复杂的选择逻辑
        """
        # 如果指定了步骤类型且有对应的agent
        if step_type and step_type in self.agents:
            return self.agents[step_type]

        # 如果有数据相关的任务，优先使用data_agent
        if step_type and ("data" in step_type.lower() or "分析" in step_type):
            data_agent = self.get_agent("data_agent")
            if data_agent:
                return data_agent

        # 默认返回主agent
        return self.primary_agent

    @abstractmethod
    async def execute(self, input_text: str) -> str:
        """执行流程的抽象方法"""
        pass

    async def cleanup(self) -> None:
        """清理所有agent资源"""
        for agent in self.agents.values():
            try:
                await agent.cleanup()
            except Exception as e:
                logger.warning(f"清理agent {agent.name} 时出错: {e}")


def create_camel_agent_wrapper(
    name: str,
    agent_instance: Any,
    description: str = ""
) -> CamelAgent:
    """
    将现有的Camel项目agent包装为BaseAgent

    Args:
        name: agent名称
        agent_instance: 实际的agent实例 (如DataAgent)
        description: agent描述

    Returns:
        包装后的CamelAgent实例
    """
    return CamelAgent(
        name=name,
        description=description,
        agent_instance=agent_instance
    )