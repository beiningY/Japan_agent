# 工具权限检查和安全审查系统

## 概述

本系统实现了在工具调用时自动启用权限检查和安全审查的功能。当Agent尝试调用工具时，系统会：

1. **权限检查**: 验证Agent是否有权限使用指定工具
2. **安全审查**: 对高风险工具进行GPT安全审查
3. **访问控制**: 根据检查结果决定是否允许工具执行

## 核心组件

### 1. SecurityReviewAgent (`agents/security_agent.py`)

主要的安全检查Agent，提供以下功能：

- `check_permission()`: 检查Agent权限
- `needs_review()`: 判断是否需要安全审查  
- `review()`: 进行完整的权限和安全检查
- `check_tool_call()`: 主要的对外接口

### 2. 权限配置 (`tools/permissions.json`)

定义了各个Agent的权限和工具的风险级别：

```json
{
  "agents": {
    "DataAgent": {
      "allowed_tools": ["list_sql_tables", "get_tables_schema", "read_sql_query"],
      "restricted_tools": []
    },
    "ViewerAgent": {
      "allowed_tools": ["list_sql_tables", "get_tables_schema"], 
      "restricted_tools": ["read_sql_query", "delete_collection", "delete_file"]
    }
  },
  "tools_info": {
    "read_sql_query": {"risk_level": "HIGH"},
    "delete_collection": {"risk_level": "HIGH"},
    "list_sql_tables": {"risk_level": "LOW"}
  }
}
```

### 3. 安全装饰器和混入类 (`utils/security_decorator.py`)

提供两种集成方式：

- `@with_security_check`: 装饰器方式
- `SecurityMixin`: 混入类方式

## 使用方法

### 方法1: 装饰器方式

```python
from utils.security_decorator import with_security_check

@with_security_check("DataAgent", "read_sql_query")
def execute_sql(query: str, action: str = "", user_query: str = ""):
    # 实际的SQL执行逻辑
    return f"执行结果: {query}"

# 使用
try:
    result = execute_sql(
        "SELECT * FROM users",
        action="SELECT * FROM users", 
        user_query="查看用户列表"
    )
except PermissionError as e:
    print(f"权限错误: {e}")
```

### 方法2: 混入类方式

```python
from utils.security_decorator import SecurityMixin

class MyAgent(SecurityMixin):
    def __init__(self):
        super().__init__()
        self.agent_name = "DataAgent"
    
    def safe_query(self, sql: str, user_query: str):
        return self.secure_tool_call(
            agent_name=self.agent_name,
            tool_id="read_sql_query",
            action=sql,
            query=user_query,
            tool_func=self._execute_sql,
            sql=sql
        )
    
    def _execute_sql(self, sql: str):
        # 实际执行逻辑
        return f"SQL结果: {sql}"
```

## 检查流程

1. **权限验证**
   - 检查Agent是否在允许列表中
   - 检查工具是否在受限列表中
   - 权限不足直接拒绝

2. **风险评估**
   - 低风险工具直接允许
   - 高风险工具进入安全审查

3. **安全审查**（仅高风险工具）
   - 调用GPT API分析操作安全性
   - 返回ALLOW/DENY/REVIEW决策

## 返回结果格式

```python
{
    "decision": "ALLOW|DENY|REVIEW",
    "reason": "决策原因说明",
    "permission_info": "权限检查信息"
}
```

- `ALLOW`: 允许执行
- `DENY`: 拒绝执行
- `REVIEW`: 需要人工审查

## 配置新的Agent和工具

### 添加新Agent

在 `permissions.json` 中添加：

```json
{
  "agents": {
    "NewAgent": {
      "allowed_tools": ["tool1", "tool2"],
      "restricted_tools": ["dangerous_tool"]
    }
  }
}
```

### 添加新工具

在 `permissions.json` 中添加：

```json
{
  "tools_info": {
    "new_tool": {"risk_level": "MEDIUM"}
  }
}
```

风险级别：
- `LOW`: 低风险，无需安全审查
- `MEDIUM`: 中等风险，可选安全审查
- `HIGH`: 高风险，强制安全审查

## 示例和测试

查看 `examples/secure_agent_example.py` 获取完整的使用示例。

运行测试：
```bash
cd Camel_agent
python examples/secure_agent_example.py
```

## 注意事项

1. **性能考虑**: 高风险工具会调用GPT API，增加延迟
2. **配置管理**: 及时更新权限配置文件
3. **错误处理**: 捕获PermissionError异常
4. **日志记录**: 系统会记录所有安全检查结果
5. **人工审查**: REVIEW状态需要实现人工审查流程

## 扩展功能

可以进一步扩展：

- 动态权限管理
- 审计日志记录
- 人工审查工作流
- 风险评分算法
- 实时监控告警
