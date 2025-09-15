"""
安全检查装饰器 - 用于在工具调用时自动启用权限和安全检查
"""
from functools import wraps
from typing import Callable, Any
import logging
from agents.security_agent import SecurityReviewAgent

logger = logging.getLogger(__name__)

def with_security_check(agent_name: str, tool_id: str):
    """
    安全检查装饰器
    
    Args:
        agent_name: 调用工具的Agent名称
        tool_id: 工具ID
    
    Usage:
        @with_security_check("DataAgent", "read_sql_query")
        def execute_sql(query: str):
            # 实际的工具执行逻辑
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            security_agent = SecurityReviewAgent()
            
            # 从参数中提取查询内容和操作描述
            action = kwargs.get('action', str(args[0] if args else ''))
            query = kwargs.get('query', kwargs.get('user_query', ''))
            
            # 进行安全检查
            check_result = security_agent.check_tool_call(
                agent_name=agent_name,
                tool_id=tool_id,
                action=action,
                query=query
            )
            
            logger.info(f"安全检查结果: {check_result}")
            
            # 根据检查结果决定是否继续执行
            if check_result["decision"] == "DENY":
                raise PermissionError(f"工具调用被拒绝: {check_result['reason']}")
            elif check_result["decision"] == "REVIEW":
                logger.warning(f"工具调用需要人工审查: {check_result['reason']}")
                # 这里可以实现人工审查流程，暂时抛出异常
                raise PermissionError(f"工具调用需要人工审查: {check_result['reason']}")
            
            # ALLOW情况下执行原函数
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


class SecurityMixin:
    """
    安全检查混入类 - 可以被其他Agent类继承
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.security_agent = SecurityReviewAgent()
    
    def check_tool_permission(self, agent_name: str, tool_id: str, action: str, query: str) -> bool:
        """
        检查工具调用权限
        
        Returns:
            bool: True表示允许执行，False表示拒绝执行
        """
        result = self.security_agent.check_tool_call(agent_name, tool_id, action, query)
        
        if result["decision"] == "ALLOW":
            return True
        elif result["decision"] == "DENY":
            logger.error(f"工具调用被拒绝: {result['reason']}")
            return False
        else:  # REVIEW
            logger.warning(f"工具调用需要人工审查: {result['reason']}")
            return False
    
    def secure_tool_call(self, agent_name: str, tool_id: str, action: str, query: str, tool_func: Callable, *args, **kwargs):
        """
        安全的工具调用方法
        
        Args:
            agent_name: Agent名称
            tool_id: 工具ID
            action: 操作描述
            query: 用户查询
            tool_func: 要执行的工具函数
            *args, **kwargs: 传递给工具函数的参数
        """
        if self.check_tool_permission(agent_name, tool_id, action, query):
            return tool_func(*args, **kwargs)
        else:
            raise PermissionError(f"Agent {agent_name} 无权限调用工具 {tool_id}")


# 使用示例
if __name__ == "__main__":
    # 装饰器使用示例
    @with_security_check("DataAgent", "read_sql_query")
    def execute_sql_query(query: str, action: str = "", user_query: str = ""):
        print(f"执行SQL查询: {query}")
        return f"查询结果: {query}"
    
    # 测试
    try:
        result = execute_sql_query(
            "SELECT * FROM users", 
            action="SELECT * FROM users",
            query="查看用户列表"
        )
        print(result)
    except PermissionError as e:
        print(f"权限错误: {e}")
    
    # 混入类使用示例
    class TestAgent(SecurityMixin):
        def __init__(self):
            super().__init__()
            self.name = "TestAgent"
        
        def safe_delete_file(self, filename: str, user_query: str):
            return self.secure_tool_call(
                agent_name=self.name,
                tool_id="delete_file",
                action=f"删除文件: {filename}",
                query=user_query,
                tool_func=self._actual_delete_file,
                filename=filename
            )
        
        def _actual_delete_file(self, filename: str):
            print(f"删除文件: {filename}")
            return f"文件 {filename} 已删除"
    
    # 测试混入类
    test_agent = TestAgent()
    try:
        result = test_agent.safe_delete_file("test.txt", "删除测试文件")
        print(result)
    except PermissionError as e:
        print(f"权限错误: {e}")