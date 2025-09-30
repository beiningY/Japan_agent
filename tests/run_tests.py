# tests/run_tests.py
"""
测试运行脚本 - 验证DataAgent和安全系统
"""

import os
import sys
import subprocess
import pytest

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def run_security_tests():
    """运行安全验证测试"""
    print("🔒 运行安全验证测试...")

    try:
        result = pytest.main([
            "tests/test_security_validation.py",
            "-v",
            "--tb=short"
        ])

        if result == 0:
            print("✅ 安全验证测试通过")
            return True
        else:
            print("❌ 安全验证测试失败")
            return False

    except Exception as e:
        print(f"❌ 安全测试运行异常: {e}")
        return False


def run_integration_tests():
    """运行集成测试"""
    print("🤖 运行DataAgent集成测试...")

    try:
        # 设置测试环境变量
        os.environ["OPENAI_API_KEY"] = "test-key-for-testing"

        result = pytest.main([
            "tests/test_data_agent_integration.py",
            "-v",
            "--tb=short"
        ])

        if result == 0:
            print("✅ DataAgent集成测试通过")
            return True
        else:
            print("❌ DataAgent集成测试失败")
            return False

    except Exception as e:
        print(f"❌ 集成测试运行异常: {e}")
        return False


def check_permissions_config():
    """检查权限配置文件"""
    print("📋 检查权限配置...")

    permissions_file = os.path.join(PROJECT_ROOT, "ToolOrchestrator/tools/permissions.json")

    if not os.path.exists(permissions_file):
        print(f"❌ 权限配置文件不存在: {permissions_file}")
        return False

    try:
        import json
        with open(permissions_file, 'r', encoding='utf-8') as f:
            permissions = json.load(f)

        # 检查必要的配置项
        if "agents" not in permissions:
            print("❌ 权限配置缺少agents配置")
            return False

        if "data-agent" not in permissions["agents"]:
            print("❌ 权限配置中缺少data-agent")
            return False

        data_agent_config = permissions["agents"]["data-agent"]
        required_fields = ["allowed_tools", "clearance_level"]

        for field in required_fields:
            if field not in data_agent_config:
                print(f"❌ data-agent配置缺少字段: {field}")
                return False

        print("✅ 权限配置检查通过")
        print(f"   - data-agent允许工具: {data_agent_config['allowed_tools']}")
        print(f"   - data-agent权限级别: {data_agent_config['clearance_level']}")
        return True

    except Exception as e:
        print(f"❌ 权限配置检查失败: {e}")
        return False


def check_code_structure():
    """检查代码结构"""
    print("🏗️ 检查代码结构...")

    required_files = [
        "agents/data_agent.py",
        "agents/mcp_toolcall_agent.py",
        "agents/react_agent.py",
        "ToolOrchestrator/core/registry.py",
        "ToolOrchestrator/core/security.py",
        "ToolOrchestrator/tools/permissions.json",
        "ToolOrchestrator/tools/config.json",
    ]

    missing_files = []

    for file_path in required_files:
        full_path = os.path.join(PROJECT_ROOT, file_path)
        if not os.path.exists(full_path):
            missing_files.append(file_path)

    if missing_files:
        print("❌ 缺少必要文件:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        return False

    print("✅ 代码结构检查通过")
    return True


def verify_imports():
    """验证关键模块导入"""
    print("📦 验证模块导入...")

    try:
        # 测试核心模块导入
        from agents.data_agent import DataAgent
        from ToolOrchestrator.core.security import SecurityValidator
        from ToolOrchestrator.core.registry import ToolRegistry

        print("✅ 核心模块导入成功")

        # 测试DataAgent实例化（不需要实际API key）
        os.environ["OPENAI_API_KEY"] = "test-key"
        agent = DataAgent()

        print(f"✅ DataAgent实例化成功: {agent.name}")

        # 测试安全验证器
        validator = SecurityValidator()
        test_result = validator.validate_sql_query("SELECT * FROM test")

        print(f"✅ 安全验证器工作正常: {test_result.allowed}")

        return True

    except Exception as e:
        print(f"❌ 模块导入失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🚀 开始DataAgent和安全系统验证\n")

    all_passed = True

    # 1. 检查代码结构
    if not check_code_structure():
        all_passed = False
    print()

    # 2. 验证模块导入
    if not verify_imports():
        all_passed = False
    print()

    # 3. 检查权限配置
    if not check_permissions_config():
        all_passed = False
    print()

    # 4. 运行安全验证测试
    if not run_security_tests():
        all_passed = False
    print()

    # 5. 运行集成测试
    if not run_integration_tests():
        all_passed = False
    print()

    # 最终结果
    if all_passed:
        print("🎉 所有测试通过！DataAgent和安全系统验证成功")
        print("\n✅ 架构验证结果:")
        print("   - DataAgent继承结构正确")
        print("   - 安全审查集中在ToolOrchestrator")
        print("   - 权限配置正确")
        print("   - 工具调用流程安全")
        return 0
    else:
        print("❌ 部分测试失败，请检查上述错误信息")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)