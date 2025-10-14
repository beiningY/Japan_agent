# 工具与权限管理指南

本文档介绍如何在工具网关（ToolOrchestrator）中添加/删除工具、修改权限，以及通过 API 进行动态注册与权限下发。

## 术语
- 工具网关: `ToolOrchestrator`（FastAPI 应用，聚合 MCP 服务端工具并统一安全校验）
- MCP 服务端: 提供具体工具实现的后端进程（如 `services/kb_server.py`, `services/db_server.py`）
- 工具注册表: `core/registry.py`，负责加载工具配置、封装安全校验并对下游调用
- 权限配置: `tools/permissions.json`，定义各 Agent 的 `allowed_tools` 等

---

## 一、添加/删除工具（配置文件方式）

工具的静态配置位于:

```
ToolOrchestrator/tools/config.json
```

每个条目示例:
```json
{
  "name": "retrieve",
  "handler": "kb_tools.retrieve",
  "description": "从指定知识库检索 top-k 片段",
  "risk_level": "LOW",
  "enabled": true,
  "parameters": {
    "type": "object",
    "properties": {
      "collection_name": {"type": "string"},
      "question": {"type": "string"},
      "k": {"type": "integer", "default": 5}
    },
    "required": ["collection_name", "question"]
  }
}
```

- `name`: 工具名称（对上层暴露）
- `handler`: 工具实现（对应 `tools/*.py` 内函数，或外部源标记）
- `risk_level`: LOW/MEDIUM/HIGH（用于权限对齐）
- `enabled`: 是否启用
- `parameters`: OpenAI function schema 兼容的 JSON Schema

添加步骤:
1. 在 `tools/*.py` 中实现函数（如 `kb_tools.py`/`db_tools.py`）
2. 在 `tools/config.json` 追加配置条目
3. 启动工具网关（或通过 API 触发注册表重载）
4. 在 `tools/permissions.json` 为目标 Agent 加入该工具（见下文）

删除步骤:
1. 从 `tools/config.json` 移除对应条目
2. 触发注册表重载（见下文 API 说明）
3. 可选: 清理权限配置中的引用

---

## 二、权限修改（permissions.json）

权限文件路径:
```
ToolOrchestrator/tools/permissions.json
```
基本结构:
```json
{
  "agents": {
    "data-agent": {
      "description": "系统内置 DataAgent",
      "allowed_tools": ["retrieve", "list_sql_tables", "get_tables_schema"],
      "restricted_tools": ["delete_collection"],
      "clearance_level": "MEDIUM",
      "agent_type": "internal"
    }
  },
  "tools_info": {
    "read_sql_query": {"risk_level": "HIGH"},
    "delete_file": {"risk_level": "HIGH"}
  }
}
```
- `allowed_tools`: 允许的工具白名单
- `restricted_tools`: 额外禁止列表（优先级更高）
- `clearance_level`: Agent 的默认权限级别（LOW/MEDIUM/HIGH）
- `tools_info`: 为工具设置风险级别（影响权限判断）

生效方式:
- 工具网关启动时加载；运行中可通过 `SecurityValidator.refresh_permissions()` 或重启进程刷新
- 调用路径: `core/registry.py -> security_validator.validate_agent_tool_access`

---

## 三、通过 API 动态管理

工具网关运行后，支持通过 REST API 动态管理工具与外部 Agent。

基础地址（默认）: `http://localhost:8000`

- 列出工具
  - `GET /api/tools`
- 执行工具
  - `POST /api/tools/execute`
  - 请求体:
    ```json
    {
      "tool_name": "retrieve",
      "arguments": {"collection_name": "japan_shrimp", "question": "溶氧标准", "k": 3},
      "user_context": {"user_clearance": "MEDIUM", "agent_name": "demo"}
    }
    ```

- 注册外部 Agent（会自动写入权限文件默认规则）
  - `POST /api/external/agents/register`
  - 返回: `access_token`（在调用工具时以 `Authorization: Bearer <token>` 传入）

- 外部 Agent 调用工具（带 token）
  - `POST /api/external/agents/call`

- 外部 Agent 可见工具
  - `GET /api/external/agents/tools`

- 注册外部 HTTP 工具（写入 `tools/config.json` 并重载）
  - `POST /api/external/tools/register`

- 注册外部 MCP 服务端及工具（批量）
  - `POST /api/external/mcp/register`

- 删除工具 / 删除 MCP 服务端
  - `DELETE /api/tools/{tool_name}`
  - `DELETE /api/external/mcp/{server_id}`

> 注: 修改配置文件后，也可通过内部重载接口 `reload_registry`（启动时会在 FastAPI lifespan 中注入 registry，可调用该函数）或重启服务来生效。

---

## 四、在 Agent 侧限制工具

对于系统内置的 `DataAgent`，在无 DB 环境变量时只暴露 `retrieve`；当设置了 `DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME` 后，会自动加入 `list_sql_tables/get_tables_schema/read_sql_query`。如果需要在 Agent 级别进一步精细控制，可在对应 Agent 的 `_ensure_tools_ready()` 中过滤。

---

## 五、常见问题（FAQ）

1) 执行工具返回 `status=error: 未授权`？
- 确认权限文件中 `agents.<agent_name>.allowed_tools` 是否包含该工具；并确保 `restricted_tools` 未覆盖禁止

2) `read_sql_query` 被拒绝，提示“只允许 SELECT”？
- SQL 安全校验仅放行 `SELECT` 语句（`core/security.py`）；避免危险关键字

3) 新增工具后在列表看不到？
- 确保该工具在下游 MCP 服务端存在；否则注册表会跳过（`registry.py` 中会检查下游工具发现结果）

4) 只做知识库检索，不想配置数据库？
- 不设置 DB_* 环境变量即可，`DataAgent` 将自动隐藏 DB 工具，仅保留 `retrieve`

---

## 六、变更流程建议

- 新增工具: 先在 `tools/*.py` 完成实现与自测 → 加配置 → 本地起网关验证 `/api/tools` 与 `/api/tools/execute` → 补权限 → 提交代码
- 权限变更: 先评审清单（涉及风险等级变更时需评审）→ 修改 `permissions.json` → 重载或重启 → 联调
- 数据库相关: 优先在 `.env` 提供 DB_*，确保测试环境可连后再放开相应工具
