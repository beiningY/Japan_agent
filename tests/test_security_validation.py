# tests/test_security_validation.py
"""
安全验证功能单元测试
"""

import pytest
import json
import tempfile
import os
from typing import Dict, Any

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ToolOrchestrator.core.security import SecurityValidator, SecurityResult, RiskLevel


class TestSecurityValidator:
    """安全验证器测试"""

    @pytest.fixture
    def temp_permissions_file(self):
        """创建临时权限配置文件"""
        permissions_data = {
            "agents": {
                "test-agent": {
                    "description": "测试agent",
                    "allowed_tools": ["list_sql_tables", "retrieve"],
                    "restricted_tools": ["delete_collection"],
                    "clearance_level": "MEDIUM"
                },
                "low-level-agent": {
                    "description": "低权限agent",
                    "allowed_tools": ["retrieve"],
                    "restricted_tools": [],
                    "clearance_level": "LOW"
                }
            },
            "tools_info": {
                "list_sql_tables": {
                    "risk_level": "LOW"
                },
                "read_sql_query": {
                    "risk_level": "HIGH"
                },
                "retrieve": {
                    "risk_level": "LOW"
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(permissions_data, f, ensure_ascii=False, indent=2)
            temp_file = f.name

        yield temp_file
        os.unlink(temp_file)

    @pytest.fixture
    def validator(self, temp_permissions_file):
        """创建安全验证器实例"""
        return SecurityValidator(temp_permissions_file)

    def test_agent_tool_access_allowed(self, validator):
        """测试允许的agent-工具访问"""
        result = validator.validate_agent_tool_access(
            agent_name="test-agent",
            tool_name="list_sql_tables",
            user_clearance="MEDIUM"
        )

        assert result.allowed is True
        assert "权限检查通过" in result.reason

    def test_agent_tool_access_restricted(self, validator):
        """测试被明确禁止的工具"""
        result = validator.validate_agent_tool_access(
            agent_name="test-agent",
            tool_name="delete_collection",
            user_clearance="HIGH"
        )

        assert result.allowed is False
        assert "被禁止使用工具" in result.reason

    def test_agent_tool_access_not_allowed(self, validator):
        """测试未授权的工具"""
        result = validator.validate_agent_tool_access(
            agent_name="test-agent",
            tool_name="unknown_tool",
            user_clearance="HIGH"
        )

        assert result.allowed is False
        assert "未被授权使用工具" in result.reason

    def test_unknown_agent(self, validator):
        """测试未知agent"""
        result = validator.validate_agent_tool_access(
            agent_name="unknown-agent",
            tool_name="list_sql_tables",
            user_clearance="HIGH"
        )

        assert result.allowed is False
        assert "未知Agent" in result.reason

    def test_clearance_level_insufficient(self, validator):
        """测试权限级别不足"""
        result = validator.validate_agent_tool_access(
            agent_name="low-level-agent",
            tool_name="read_sql_query",  # HIGH风险工具
            user_clearance="LOW"
        )

        # 由于工具不在allowed_tools中，应该被拒绝
        assert result.allowed is False

    def test_sql_query_validation_select(self, validator):
        """测试合法的SELECT查询"""
        queries = [
            "SELECT * FROM users",
            "select id, name from products where price > 100",
            "  SELECT count(*) FROM orders  ",
        ]

        for query in queries:
            result = validator.validate_sql_query(query)
            assert result.allowed is True, f"查询应该被允许: {query}"

    def test_sql_query_validation_dangerous(self, validator):
        """测试危险的SQL查询"""
        dangerous_queries = [
            "DROP TABLE users",
            "DELETE FROM products",
            "INSERT INTO admin VALUES (1, 'hacker')",
            "UPDATE users SET password = 'hacked'",
            "ALTER TABLE users ADD COLUMN hacked text",
            "CREATE TABLE backdoor (id int)",
            "TRUNCATE TABLE logs",
            "EXEC sp_executesql 'malicious code'",
        ]

        for query in dangerous_queries:
            result = validator.validate_sql_query(query)
            assert result.allowed is False, f"危险查询应该被拒绝: {query}"
            assert "危险关键词" in result.reason or "只允许SELECT" in result.reason

    def test_sql_query_validation_invalid_input(self, validator):
        """测试无效的SQL输入"""
        invalid_inputs = [None, "", "   ", 123, []]

        for invalid_input in invalid_inputs:
            result = validator.validate_sql_query(invalid_input)
            assert result.allowed is False
            assert "无效的SQL查询" in result.reason

    def test_file_path_validation_safe(self, validator):
        """测试安全的文件路径"""
        safe_paths = [
            "data/report.txt",
            "documents/analysis.pdf",
            "uploads/image.jpg",
            "logs/app.log",
        ]

        for path in safe_paths:
            result = validator.validate_file_path(path)
            assert result.allowed is True, f"安全路径应该被允许: {path}"

    def test_file_path_validation_dangerous(self, validator):
        """测试危险的文件路径"""
        dangerous_paths = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config",
            "/etc/shadow",
            "data/../../../etc/hosts",
            "C:\\Windows\\System32\\drivers\\etc\\hosts",
        ]

        for path in dangerous_paths:
            result = validator.validate_file_path(path)
            assert result.allowed is False, f"危险路径应该被拒绝: {path}"

    def test_file_path_validation_dangerous_extensions(self, validator):
        """测试危险的文件扩展名"""
        dangerous_files = [
            "malware.exe",
            "script.bat",
            "backdoor.sh",
            "virus.py",
            "trojan.js",
        ]

        for file_path in dangerous_files:
            result = validator.validate_file_path(file_path)
            assert result.allowed is False, f"危险文件类型应该被拒绝: {file_path}"
            assert "不允许的文件类型" in result.reason

    def test_risk_level_mapping(self, validator):
        """测试风险级别映射"""
        # 测试权限级别到数值的转换
        assert validator._clearance_to_int("LOW") == 0
        assert validator._clearance_to_int("MEDIUM") == 1
        assert validator._clearance_to_int("HIGH") == 2
        assert validator._clearance_to_int("INVALID") == 0  # 默认值

        # 测试数值到权限级别的转换
        assert validator._int_to_clearance(0) == "LOW"
        assert validator._int_to_clearance(1) == "MEDIUM"
        assert validator._int_to_clearance(2) == "HIGH"
        assert validator._int_to_clearance(99) == "LOW"  # 默认值

    def test_tool_risk_level_detection(self, validator):
        """测试工具风险级别检测"""
        # 从配置文件中获取
        assert validator._get_tool_risk_level("list_sql_tables") == "LOW"
        assert validator._get_tool_risk_level("read_sql_query") == "HIGH"

        # 基于名称推断
        assert validator._get_tool_risk_level("delete_something") == "HIGH"
        assert validator._get_tool_risk_level("create_user") == "MEDIUM"
        assert validator._get_tool_risk_level("get_info") == "LOW"

    def test_permissions_cache_refresh(self, validator):
        """测试权限配置缓存刷新"""
        # 第一次访问会加载配置
        result1 = validator.validate_agent_tool_access("test-agent", "list_sql_tables")
        assert result1.allowed is True

        # 刷新缓存
        validator.refresh_permissions()
        assert validator._permissions_cache is None

        # 再次访问会重新加载
        result2 = validator.validate_agent_tool_access("test-agent", "list_sql_tables")
        assert result2.allowed is True

    def test_security_result_serialization(self):
        """测试安全结果序列化"""
        result = SecurityResult(
            allowed=True,
            reason="测试通过",
            risk_level="MEDIUM"
        )

        result_dict = result.to_dict()
        assert result_dict["allowed"] is True
        assert result_dict["reason"] == "测试通过"
        assert result_dict["risk_level"] == "MEDIUM"


class TestRiskLevelEnum:
    """风险级别枚举测试"""

    def test_risk_level_values(self):
        """测试风险级别枚举值"""
        assert RiskLevel.LOW == "LOW"
        assert RiskLevel.MEDIUM == "MEDIUM"
        assert RiskLevel.HIGH == "HIGH"

    def test_risk_level_comparison(self):
        """测试风险级别比较"""
        # 这里可以添加风险级别比较的逻辑测试
        risk_levels = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH]
        assert len(risk_levels) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])