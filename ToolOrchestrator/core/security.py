# core/security.py
"""
简化版安全控制模块 - 统一权限检查和安全验证
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger("Security")


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class SecurityResult:
    """安全检查结果"""
    def __init__(self, allowed: bool, reason: str = "", risk_level: str = "MEDIUM"):
        self.allowed = allowed
        self.reason = reason
        self.risk_level = risk_level

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "risk_level": self.risk_level
        }


class SecurityValidator:
    """统一安全验证器 - 简化版"""

    def __init__(self, permissions_file: str = "ToolOrchestrator/tools/permissions.json"):
        self.permissions_file = permissions_file
        self._permissions_cache: Optional[Dict] = None

    def _load_permissions(self) -> Dict:
        """加载权限配置"""
        if self._permissions_cache is None:
            try:
                with open(self.permissions_file, "r", encoding="utf-8") as f:
                    self._permissions_cache = json.load(f)
            except Exception as e:
                logger.error(f"加载权限配置失败: {e}")
                self._permissions_cache = {"agents": {}, "tools_info": {}}
        return self._permissions_cache

    def validate_agent_tool_access(
        self,
        agent_name: str,
        tool_name: str,
        user_clearance: str = "LOW"
    ) -> SecurityResult:
        """验证agent对工具的访问权限"""

        permissions = self._load_permissions()
        agents = permissions.get("agents", {})

        # 1. 检查agent是否存在
        if agent_name not in agents:
            return SecurityResult(
                allowed=False,
                reason=f"未知Agent: {agent_name}"
            )

        agent_config = agents[agent_name]

        # 2. 检查是否被明确禁止
        if tool_name in agent_config.get("restricted_tools", []):
            return SecurityResult(
                allowed=False,
                reason=f"Agent {agent_name} 被禁止使用工具 {tool_name}"
            )

        # 3. 检查是否在允许列表中
        if tool_name not in agent_config.get("allowed_tools", []):
            return SecurityResult(
                allowed=False,
                reason=f"Agent {agent_name} 未被授权使用工具 {tool_name}"
            )

        # 4. 检查用户权限级别
        tool_risk = self._get_tool_risk_level(tool_name)
        agent_clearance = agent_config.get("clearance_level", "LOW")

        # 使用agent的权限级别，如果用户权限更低则使用用户权限
        effective_clearance = min(
            self._clearance_to_int(agent_clearance),
            self._clearance_to_int(user_clearance)
        )

        if effective_clearance < self._clearance_to_int(tool_risk):
            return SecurityResult(
                allowed=False,
                reason=f"权限级别不足: 需要{tool_risk}，当前{self._int_to_clearance(effective_clearance)}",
                risk_level=tool_risk
            )

        return SecurityResult(
            allowed=True,
            reason="权限检查通过",
            risk_level=tool_risk
        )

    def validate_sql_query(self, query: str) -> SecurityResult:
        """简化的SQL安全检查"""
        if not query or not isinstance(query, str) or not query.strip():
            return SecurityResult(
                allowed=False,
                reason="无效的SQL查询"
            )

        # 基础安全检查 - 只允许SELECT语句
        query_lower = query.lower().strip()

        # 检查是否以SELECT开头
        if not query_lower.startswith('select'):
            return SecurityResult(
                allowed=False,
                reason="只允许SELECT查询"
            )

        # 检查危险关键词
        dangerous_keywords = [
            'drop', 'delete', 'insert', 'update', 'alter',
            'create', 'truncate', 'exec', 'execute'
        ]

        for keyword in dangerous_keywords:
            if re.search(rf'\b{keyword}\b', query_lower):
                return SecurityResult(
                    allowed=False,
                    reason=f"包含危险关键词: {keyword}"
                )

        return SecurityResult(
            allowed=True,
            reason="SQL查询安全检查通过"
        )

    def validate_file_path(self, file_path: str) -> SecurityResult:
        """文件路径安全检查"""
        if not file_path or not isinstance(file_path, str):
            return SecurityResult(
                allowed=False,
                reason="无效的文件路径"
            )

        # 检查路径遍历攻击
        if '..' in file_path or file_path.startswith('/') or (len(file_path) > 2 and file_path[1] == ':'):
            return SecurityResult(
                allowed=False,
                reason="检测到路径遍历攻击"
            )

        # 检查危险文件扩展名
        dangerous_extensions = ['.exe', '.bat', '.sh', '.py', '.js']
        if any(file_path.lower().endswith(ext) for ext in dangerous_extensions):
            return SecurityResult(
                allowed=False,
                reason="不允许的文件类型"
            )

        return SecurityResult(
            allowed=True,
            reason="文件路径检查通过"
        )

    def _get_tool_risk_level(self, tool_name: str) -> str:
        """获取工具风险级别"""
        permissions = self._load_permissions()
        tools_info = permissions.get("tools_info", {})

        if tool_name in tools_info:
            return tools_info[tool_name].get("risk_level", "MEDIUM")

        # 默认风险级别判断
        if any(keyword in tool_name.lower() for keyword in ['delete', 'remove', 'drop']):
            return "HIGH"
        elif any(keyword in tool_name.lower() for keyword in ['create', 'add', 'update']):
            return "MEDIUM"
        else:
            return "LOW"

    def _clearance_to_int(self, clearance: str) -> int:
        """权限级别转数值"""
        mapping = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
        return mapping.get(clearance.upper(), 0)

    def _int_to_clearance(self, level: int) -> str:
        """数值转权限级别"""
        mapping = {0: "LOW", 1: "MEDIUM", 2: "HIGH"}
        return mapping.get(level, "LOW")

    def refresh_permissions(self):
        """刷新权限缓存"""
        self._permissions_cache = None
        logger.info("权限配置缓存已刷新")


# 全局安全验证器实例
security_validator = SecurityValidator()