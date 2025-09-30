# flow/factory.py
"""
FlowFactory - 流程工厂类

提供创建不同类型流程的工厂方法，适配Camel_agent项目
"""

from __future__ import annotations
from enum import Enum
from typing import Dict, List, Union, Any, Optional
from dataclasses import dataclass
import logging

from .base import BaseFlow, BaseAgent
from .planning import PlanningFlow

logger = logging.getLogger(__name__)


class FlowType(str, Enum):
    """流程类型枚举"""
    PLANNING = "planning"
    # 可以在此添加更多流程类型
    # SEQUENTIAL = "sequential"
    # PARALLEL = "parallel"
    # CONDITIONAL = "conditional"


@dataclass
class FlowFactory:
    """
    流程工厂 - 创建不同类型的执行流程

    支持多智能体协作，适配Camel_agent项目架构
    """

    @staticmethod
    def create_flow(
        flow_type: FlowType,
        agents: Union[BaseAgent, List[BaseAgent], Dict[str, BaseAgent]],
        **kwargs
    ) -> BaseFlow:
        """
        创建指定类型的流程

        Args:
            flow_type: 流程类型
            agents: 参与的智能体（可以是单个、列表或字典）
            **kwargs: 其他流程配置参数

        Returns:
            创建的流程实例

        Raises:
            ValueError: 未知的流程类型
        """

        # 标准化agents为字典格式
        agents_dict = FlowFactory._normalize_agents(agents)

        # 根据流程类型创建对应的流程
        if flow_type == FlowType.PLANNING:
            return FlowFactory._create_planning_flow(agents_dict, **kwargs)
        else:
            raise ValueError(f"未知的流程类型: {flow_type}")

    @staticmethod
    def _normalize_agents(
        agents: Union[BaseAgent, List[BaseAgent], Dict[str, BaseAgent]]
    ) -> Dict[str, BaseAgent]:
        """
        将不同格式的agents标准化为字典格式

        Args:
            agents: 输入的agents

        Returns:
            标准化后的agents字典
        """

        if isinstance(agents, BaseAgent):
            # 单个agent
            return {"default": agents}
        elif isinstance(agents, list):
            # agent列表
            agents_dict = {}
            for i, agent in enumerate(agents):
                key = getattr(agent, 'name', f"agent_{i}")
                agents_dict[key] = agent
            return agents_dict
        elif isinstance(agents, dict):
            # 已经是字典格式
            return agents
        else:
            raise ValueError(f"不支持的agents类型: {type(agents)}")

    @staticmethod
    def _create_planning_flow(
        agents_dict: Dict[str, BaseAgent],
        **kwargs
    ) -> PlanningFlow:
        """
        创建规划流程

        Args:
            agents_dict: agents字典
            **kwargs: 其他配置参数

        Returns:
            PlanningFlow实例
        """

        # 设置主agent
        primary_agent_key = kwargs.get("primary_agent_key")
        if not primary_agent_key and agents_dict:
            primary_agent_key = next(iter(agents_dict))

        # 创建PlanningFlow实例
        flow = PlanningFlow(
            agents=agents_dict,
            primary_agent_key=primary_agent_key,
            config=kwargs.get("config", {})
        )

        # 设置特定配置
        if "plan_id" in kwargs:
            flow.active_plan_id = kwargs["plan_id"]

        if "planning_tool" in kwargs:
            flow.planning_tool = kwargs["planning_tool"]

        return flow

    @staticmethod
    def get_available_flow_types() -> List[str]:
        """获取所有可用的流程类型"""
        return [flow_type.value for flow_type in FlowType]

    @staticmethod
    def create_flow_from_config(config: Dict[str, Any]) -> BaseFlow:
        """
        从配置字典创建流程

        Args:
            config: 配置字典，包含flow_type, agents等信息

        Returns:
            创建的流程实例

        Example:
            config = {
                "flow_type": "planning",
                "agents": {
                    "data_agent": data_agent_instance,
                    "mcp_agent": mcp_agent_instance
                },
                "primary_agent_key": "data_agent",
                "plan_id": "custom_plan_123"
            }
        """

        flow_type_str = config.get("flow_type")
        if not flow_type_str:
            raise ValueError("配置中必须包含flow_type")

        try:
            flow_type = FlowType(flow_type_str)
        except ValueError:
            raise ValueError(f"不支持的流程类型: {flow_type_str}")

        agents = config.get("agents")
        if not agents:
            raise ValueError("配置中必须包含agents")

        # 移除已处理的配置项，剩余的作为kwargs传递
        kwargs = {k: v for k, v in config.items() if k not in ["flow_type", "agents"]}

        return FlowFactory.create_flow(flow_type, agents, **kwargs)


class FlowRegistry:
    """
    流程注册表 - 管理和缓存流程实例

    提供流程的创建、获取、删除等管理功能
    """

    def __init__(self):
        self._flows: Dict[str, BaseFlow] = {}
        self._flow_configs: Dict[str, Dict[str, Any]] = {}

    def register_flow(self, flow_id: str, flow: BaseFlow, config: Optional[Dict[str, Any]] = None) -> None:
        """
        注册流程实例

        Args:
            flow_id: 流程唯一标识
            flow: 流程实例
            config: 流程配置（可选）
        """
        self._flows[flow_id] = flow
        if config:
            self._flow_configs[flow_id] = config

        logger.info(f"流程已注册: {flow_id}")

    def get_flow(self, flow_id: str) -> Optional[BaseFlow]:
        """获取流程实例"""
        return self._flows.get(flow_id)

    def create_and_register_flow(
        self,
        flow_id: str,
        flow_type: FlowType,
        agents: Union[BaseAgent, List[BaseAgent], Dict[str, BaseAgent]],
        **kwargs
    ) -> BaseFlow:
        """
        创建并注册流程

        Args:
            flow_id: 流程唯一标识
            flow_type: 流程类型
            agents: 参与的智能体
            **kwargs: 其他配置参数

        Returns:
            创建的流程实例
        """

        flow = FlowFactory.create_flow(flow_type, agents, **kwargs)
        config = {
            "flow_type": flow_type.value,
            "agents": agents,
            **kwargs
        }

        self.register_flow(flow_id, flow, config)
        return flow

    def remove_flow(self, flow_id: str) -> bool:
        """
        移除流程

        Args:
            flow_id: 流程标识

        Returns:
            是否成功移除
        """

        if flow_id in self._flows:
            flow = self._flows[flow_id]
            # 清理流程资源
            try:
                import asyncio
                asyncio.create_task(flow.cleanup())
            except Exception as e:
                logger.warning(f"清理流程 {flow_id} 时出错: {e}")

            del self._flows[flow_id]
            if flow_id in self._flow_configs:
                del self._flow_configs[flow_id]

            logger.info(f"流程已移除: {flow_id}")
            return True

        return False

    def list_flows(self) -> List[Dict[str, Any]]:
        """
        列出所有注册的流程

        Returns:
            流程信息列表
        """

        flows_info = []
        for flow_id, flow in self._flows.items():
            config = self._flow_configs.get(flow_id, {})
            flows_info.append({
                "flow_id": flow_id,
                "flow_type": config.get("flow_type", "unknown"),
                "agents_count": len(flow.agents),
                "primary_agent": flow.primary_agent_key,
                "config": config
            })

        return flows_info

    def clear_all(self) -> None:
        """清空所有流程"""

        for flow_id in list(self._flows.keys()):
            self.remove_flow(flow_id)


# 全局流程注册表实例
flow_registry = FlowRegistry()