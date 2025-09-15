"""
权限与MCP工具策略管理
基于 JSON 的角色权限与 MCP 工具访问控制、参数校验与速率限制。
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


logger = logging.getLogger("permission_manager")


class UserRole(Enum):
    ADMIN = "admin"
    SECURITY_AUDITOR = "security_auditor"
    DBA = "dba"
    DEVELOPER = "developer"
    READONLY = "readonly"


class Permission(Enum):
    DB_READ = "db:read"
    DB_WRITE = "db:write"
    DB_SCHEMA = "db:schema"
    DB_ADMIN = "db:admin"

    SECURITY_CODE_REVIEW = "security:code_review"
    SECURITY_SQL_REVIEW = "security:sql_review"
    SECURITY_CONFIG_REVIEW = "security:config_review"
    SECURITY_REPORT_GENERATE = "security:report_generate"

    SYSTEM_ADMIN = "system:admin"
    AUDIT_READ = "audit:read"


@dataclass
class MCPToolRule:
    name: str
    required_permission: Optional[str]
    sensitivity: str
    allowed_roles: List[str]
    rate_limit_per_minute: Optional[int]
    approval_required: bool
    allowed_params: Dict[str, Dict[str, List[str]]]


class PermissionManager:
    def __init__(
        self,
        role_config_path: str = "/usr/sarah/Camel_agent/config/permission_config.json",
        mcp_policy_path: str = "/usr/sarah/Camel_agent/config/mcp_tool_policy.json",
    ) -> None:
        self.role_config_path = role_config_path
        self.mcp_policy_path = mcp_policy_path
        self.role_permissions: Dict[str, Set[str]] = {}
        self.users: Dict[str, Dict[str, Any]] = {}
        self.mcp_rules: Dict[str, MCPToolRule] = {}
        self.default_unknown_action: str = "deny"
        # 简单速率限制桶: key=(username, tool) -> [timestamps]
        self._rate_buckets: Dict[Tuple[str, str], List[float]] = {}
        self.load_configs()

    def load_configs(self) -> None:
        # 加载角色与用户配置
        try:
            with open(self.role_config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.role_permissions = {
                role: set(perms) for role, perms in data.get("role_permissions", {}).items()
            }
            self.users = data.get("users", {})
            logger.info("角色权限配置加载成功")
        except FileNotFoundError:
            logger.warning("permission_config.json 未找到，将使用空配置")
            self.role_permissions = {}
            self.users = {}
        except Exception as e:
            logger.error(f"加载角色权限配置失败: {e}")
            self.role_permissions = {}
            self.users = {}

        # 加载 MCP 工具策略
        try:
            with open(self.mcp_policy_path, "r", encoding="utf-8") as f:
                policy = json.load(f)
            self.default_unknown_action = policy.get("default_policy", {}).get(
                "unknown_tool_action", "deny"
            )
            tools_dict = policy.get("tools", {})
            parsed: Dict[str, MCPToolRule] = {}
            for tool_name, rule in tools_dict.items():
                parsed[tool_name] = MCPToolRule(
                    name=tool_name,
                    required_permission=rule.get("required_permission"),
                    sensitivity=rule.get("sensitivity", "LOW"),
                    allowed_roles=rule.get("allowed_roles", []),
                    rate_limit_per_minute=rule.get("rate_limit_per_minute"),
                    approval_required=bool(rule.get("approval_required", False)),
                    allowed_params=rule.get("allowed_params", {}),
                )
            self.mcp_rules = parsed
            logger.info("MCP 工具策略加载成功")
        except FileNotFoundError:
            logger.warning("mcp_tool_policy.json 未找到，所有未知工具将按 deny 处理")
            self.mcp_rules = {}
        except Exception as e:
            logger.error(f"加载 MCP 工具策略失败: {e}")
            self.mcp_rules = {}

    def get_user_info(self, username: str) -> Optional[Dict[str, Any]]:
        return self.users.get(username)

    def get_user_role(self, username: str) -> Optional[str]:
        user = self.get_user_info(username)
        return user.get("role") if user else None

    def get_user_permissions(self, username: str) -> Set[str]:
        role = self.get_user_role(username)
        if not role:
            return set()
        return self.role_permissions.get(role, set())

    def check_permission(self, username: str, permission: str) -> bool:
        return permission in self.get_user_permissions(username)

    def filter_mcp_tools_for_user(self, username: str, tools: List[Any]) -> List[Any]:
        role = self.get_user_role(username)
        if not role:
            return []

        filtered: List[Any] = []
        for t in tools:
            name = getattr(t, "name", None) or (t if isinstance(t, str) else None)
            if not name:
                continue
            allowed, _ = self.check_mcp_tool_access(username, name, {})
            if allowed:
                filtered.append(t)
        return filtered

    def check_mcp_tool_access(
        self,
        username: str,
        tool_name: str,
        params: Dict[str, Any] | None,
        *,
        approved: bool = False,
    ) -> Tuple[bool, str]:
        params = params or {}
        role = self.get_user_role(username)
        if not role:
            return False, "用户无角色信息"

        rule = self.mcp_rules.get(tool_name)
        if not rule:
            if self.default_unknown_action == "allow":
                return True, "未知工具按 allow 策略放行"
            return False, "未知工具，策略拒绝"

        # 角色白名单
        if rule.allowed_roles and role not in rule.allowed_roles:
            return False, "角色未被允许访问该工具"

        # 权限检查
        if rule.required_permission and not self.check_permission(username, rule.required_permission):
            return False, f"缺少权限: {rule.required_permission}"

        # 是否需要审批
        if rule.approval_required and not approved:
            return False, "需要审批"

        # 参数正则拦截
        for param_name, param_rules in (rule.allowed_params or {}).items():
            if param_name in params:
                value = params[param_name]
                if value is None:
                    continue
                value_str = str(value)
                for pattern in param_rules.get("deny_patterns", []):
                    try:
                        if re.search(pattern, value_str):
                            return False, f"参数 {param_name} 触发拦截规则"
                    except re.error:
                        logger.warning(f"无效的正则: {pattern}")

        # 速率限制
        if rule.rate_limit_per_minute:
            if not self._check_rate_limit(username, tool_name, rule.rate_limit_per_minute):
                return False, "超出速率限制"

        return True, "允许"

    def _check_rate_limit(self, username: str, tool_name: str, limit_per_min: int) -> bool:
        key = (username, tool_name)
        now = time.time()
        window_start = now - 60.0
        bucket = self._rate_buckets.setdefault(key, [])
        # 清理窗口之外
        i = 0
        for i in range(len(bucket)):
            if bucket[i] >= window_start:
                break
        if i > 0:
            del bucket[:i]
        if len(bucket) >= limit_per_min:
            return False
        bucket.append(now)
        return True


# 全局实例
permission_manager = PermissionManager()


