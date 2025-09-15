"""
安全Agent示例 - 展示如何在现有Agent中集成权限检查
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.security_decorator import with_security_check, SecurityMixin
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecureDataAgent(SecurityMixin):
    """
    带安全检查的数据Agent示例
    """
    
    def __init__(self):
        super().__init__()
        self.agent_name = "DataAgent"
    
    def list_tables(self, user_query: str = ""):
        """安全的表列表查询"""
        return self.secure_tool_call(
            agent_name=self.agent_name,
            tool_id="list_sql_tables",
            action="SHOW TABLES",
            query=user_query,
            tool_func=self._execute_list_tables
        )
    
    def _execute_list_tables(self):
        """实际的表列表查询实现"""
        logger.info("执行表列表查询")
        return ["users", "products", "orders"]
    
    def execute_query(self, sql: str, user_query: str = ""):
        """安全的SQL查询执行"""
        return self.secure_tool_call(
            agent_name=self.agent_name,
            tool_id="read_sql_query",
            action=sql,
            query=user_query,
            tool_func=self._execute_sql,
            sql=sql
        )
    
    def _execute_sql(self, sql: str):
        """实际的SQL执行实现"""
        logger.info(f"执行SQL: {sql}")
        return f"SQL执行结果: {sql}"


class SecureKnowledgeAgent(SecurityMixin):
    """
    带安全检查的知识Agent示例
    """
    
    def __init__(self):
        super().__init__()
        self.agent_name = "KnowledgeAgent"
    
    def create_collection(self, collection_name: str, user_query: str = ""):
        """安全的集合创建"""
        return self.secure_tool_call(
            agent_name=self.agent_name,
            tool_id="create_collection",
            action=f"创建集合: {collection_name}",
            query=user_query,
            tool_func=self._create_collection,
            collection_name=collection_name
        )
    
    def _create_collection(self, collection_name: str):
        """实际的集合创建实现"""
        logger.info(f"创建集合: {collection_name}")
        return f"集合 {collection_name} 创建成功"
    
    def delete_collection(self, collection_name: str, user_query: str = ""):
        """安全的集合删除"""
        return self.secure_tool_call(
            agent_name=self.agent_name,
            tool_id="delete_collection",
            action=f"删除集合: {collection_name}",
            query=user_query,
            tool_func=self._delete_collection,
            collection_name=collection_name
        )
    
    def _delete_collection(self, collection_name: str):
        """实际的集合删除实现"""
        logger.info(f"删除集合: {collection_name}")
        return f"集合 {collection_name} 删除成功"


# 使用装饰器的示例
@with_security_check("ViewerAgent", "read_sql_query")
def viewer_execute_query(query: str, action: str = "", user_query: str = ""):
    """ViewerAgent尝试执行SQL查询（应该被拒绝）"""
    logger.info(f"ViewerAgent执行查询: {query}")
    return f"查询结果: {query}"


def main():
    """主测试函数"""
    print("=== 安全Agent集成示例 ===\n")
    
    # 测试DataAgent
    print("1. 测试DataAgent:")
    data_agent = SecureDataAgent()
    
    try:
        # 低风险操作 - 应该成功
        result = data_agent.list_tables("查看数据库表")
        print(f"✅ 列表查询成功: {result}")
    except PermissionError as e:
        print(f"❌ 权限错误: {e}")
    
    try:
        # 高风险操作但权限足够 - 需要安全审查
        result = data_agent.execute_query("SELECT * FROM users", "查看用户信息")
        print(f"✅ SQL查询成功: {result}")
    except PermissionError as e:
        print(f"❌ 权限错误: {e}")
    
    print("\n" + "-"*50 + "\n")
    
    # 测试KnowledgeAgent
    print("2. 测试KnowledgeAgent:")
    knowledge_agent = SecureKnowledgeAgent()
    
    try:
        # 低风险操作 - 应该成功
        result = knowledge_agent.create_collection("test_collection", "创建测试集合")
        print(f"✅ 创建集合成功: {result}")
    except PermissionError as e:
        print(f"❌ 权限错误: {e}")
    
    try:
        # 高风险操作 - 需要安全审查
        result = knowledge_agent.delete_collection("test_collection", "删除测试集合")
        print(f"✅ 删除集合成功: {result}")
    except PermissionError as e:
        print(f"❌ 权限错误: {e}")
    
    print("\n" + "-"*50 + "\n")
    
    # 测试ViewerAgent（权限不足）
    print("3. 测试ViewerAgent（权限不足的场景）:")
    try:
        result = viewer_execute_query(
            "SELECT * FROM users",
            action="SELECT * FROM users",
            user_query="查看用户信息"
        )
        print(f"✅ ViewerAgent查询成功: {result}")
    except PermissionError as e:
        print(f"❌ ViewerAgent权限错误: {e}")


if __name__ == "__main__":
    main()
