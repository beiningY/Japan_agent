# flow/__init__.py
"""
Flow系统模块 - 多智能体协作规划框架

基于OpenManus的flow架构设计，适配Camel_agent项目特点
"""

from .base import BaseFlow
from .planning import PlanningFlow
from .factory import FlowFactory, FlowType

__all__ = [
    "BaseFlow",
    "PlanningFlow",
    "FlowFactory",
    "FlowType"
]