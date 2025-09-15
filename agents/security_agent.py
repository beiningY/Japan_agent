from openai import OpenAI
import json
import os

class SecurityReviewAgent:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("GPT_API_KEY"))
        with open("tools/permissions.json", "r") as f:
            data = json.load(f)
        self.tools_info = data["tools_info"]
        self.agents_permissions = data["agents"]

    def check_permission(self, agent_name: str, tool_id: str) -> dict:
        """检查agent是否有权限使用指定工具"""
        # 检查agent是否存在
        if agent_name not in self.agents_permissions:
            return {
                "allowed": False, 
                "reason": f"未知的Agent: {agent_name}"
            }
        
        agent_perms = self.agents_permissions[agent_name]
        
        # 检查是否在受限工具列表中
        if tool_id in agent_perms.get("restricted_tools", []):
            return {
                "allowed": False,
                "reason": f"Agent {agent_name} 被明确禁止使用工具 {tool_id}"
            }
        
        # 检查是否在允许工具列表中
        if tool_id in agent_perms.get("allowed_tools", []):
            return {
                "allowed": True,
                "reason": f"Agent {agent_name} 有权限使用工具 {tool_id}"
            }
        
        # 工具不在任何列表中，默认拒绝
        return {
            "allowed": False,
            "reason": f"Agent {agent_name} 未被授权使用工具 {tool_id}"
        }

    def needs_review(self, tool_id: str) -> bool:
        """是否需要触发安全审查"""
        if tool_id not in self.tools_info:
            return False
        return self.tools_info[tool_id]["risk_level"] == "HIGH"

    def review(self, agent_name: str, tool_id: str, action: str, query: str) -> dict:
        """进行完整的权限和安全审查，返回 ALLOW/DENY/REVIEW 三种结果"""
        # 首先检查权限
        permission_check = self.check_permission(agent_name, tool_id)
        if not permission_check["allowed"]:
            return {
                "decision": "DENY", 
                "reason": f"权限检查失败: {permission_check['reason']}"
            }
        
        # 权限通过后，检查是否需要安全审查
        if not self.needs_review(tool_id):
            return {
                "decision": "ALLOW", 
                "reason": f"权限检查通过，低风险工具无需安全审查。{permission_check['reason']}"
            }

        input_prompt = f"""
你是一个安全审查Agent。
Agent {agent_name} 请求调用工具 {tool_id}进行操作：{action}。
用户的提问或要求是：{query}

请从安全角度给出判断：
- 如果操作明显安全，可以直接放行：返回 ALLOW
- 如果操作明显违规或危险，必须禁止：返回 DENY
- 如果情况模糊不清，需要人工进一步确认：返回 REVIEW

只返回 JSON 格式，例如：
{{"decision": "ALLOW", "reason": "..." }}
"""

        response = self.client.responses.create(
            model="gpt-5",
            instructions="你是一个安全审查Agent。",
            input=input_prompt,
        )

        try:
            content = response.output_text.strip()
            result = json.loads(content)
            # 确保权限检查信息也包含在最终结果中
            result["permission_info"] = permission_check["reason"]
            return result
        except Exception as e:
            return {"decision": "REVIEW", "reason": f"解析失败，进入人工复审: {e}", "permission_info": permission_check["reason"]}

    def check_tool_call(self, agent_name: str, tool_id: str, action: str, query: str) -> dict:
        """工具调用的完整检查流程 - 这是主要的对外接口"""
        return self.review(agent_name, tool_id, action, query)


# 示例和测试
if __name__ == "__main__":
    agent = SecurityReviewAgent()

    print("=== 权限和安全检查测试 ===\n")

    tests = [
        # 权限检查测试
        ("ViewerAgent", "read_sql_query", "SELECT * FROM users;", "查看用户列表"),  # 应该被拒绝 - 权限不足
        ("UnknownAgent", "list_sql_tables", "SHOW TABLES;", "查看数据库表"),  # 应该被拒绝 - 未知Agent
        ("DataAgent", "list_sql_tables", "SHOW TABLES;", "查看数据库表"),  # 应该通过 - 低风险
        ("KnowledgeAgent", "create_file", "创建配置文件", "创建配置文件"),  # 应该通过 - 中等风险
        
        # 安全审查测试（高风险工具）
        ("DataAgent", "read_sql_query", "DROP TABLE users;","users列表是什么结构"),  # 高风险，需要安全审查
        ("KnowledgeAgent", "delete_collection", "删除测试集合","删除测试集合"),  # 高风险，需要安全审查
        ("KnowledgeAgent", "delete_file", "rm -rf /", "删除所有文件"),  # 高风险且危险操作
    ]

    for i, (ag, tool, action, q) in enumerate(tests, 1):
        print(f"测试 {i}: {ag} 使用 {tool}")
        result = agent.check_tool_call(ag, tool, action, q)
        print(f"结果: {result}")
        print("-" * 50)
    # 调用SecurityReviewAgent类用reviwe方法进行审查，并打印结果
    # 结果{'decision': 'DENY', 'reason': "该请求尝试执行 DROP TABLE users;，这是破坏性操作（删除数据表及其数据），与用户仅询问表结构的需求不符，存在高风险。应使用只读查询获取结构（如 DESCRIBE users、SHOW COLUMNS FROM users 或 PRAGMA table_info('users')）。"}
    #    {'decision': 'REVIEW', 'reason': '该请求将执行不可逆的数据删除操作。虽然描述为“测试集合”，但缺乏对集合标识、环境（开发/测试/生产）、用户权限及备份状况的确认，存在误删与数据丢失风险，需人工进一步确认后再执行。'}
    #    {'decision': 'ALLOW', 'reason': '低风险工具，无需审查'}