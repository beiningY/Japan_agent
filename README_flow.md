# Flow系统 - 多智能体协作规划框架

基于OpenManus的flow架构设计，为Camel_agent项目提供多智能体协作的规划和执行能力。

## 🎯 核心特性

- **智能规划**: 自动将复杂任务分解为可执行的步骤
- **多智能体协作**: 支持不同类型智能体协同工作
- **状态跟踪**: 实时跟踪计划执行状态和进度
- **灵活配置**: 支持自定义流程类型和执行策略
- **错误处理**: 完善的异常处理和恢复机制

## 🏗️ 架构设计

```
flow/
├── __init__.py          # 模块导出
├── base.py             # BaseFlow基础类和Agent包装器
├── planning_tool.py    # 规划管理工具
├── planning.py         # PlanningFlow规划流程
└── factory.py          # FlowFactory工厂类和注册表
```

### 核心组件

1. **BaseFlow**: 流程基础类，定义多智能体协作接口
2. **PlanningFlow**: 规划执行流程，支持自动任务分解和执行
3. **PlanningTool**: 规划管理工具，提供计划CRUD操作
4. **FlowFactory**: 流程工厂，创建不同类型的流程
5. **FlowRegistry**: 流程注册表，管理多个流程实例

## 🚀 快速开始

### 1. 基础使用

```python
from flow import FlowFactory, FlowType
from flow.base import create_camel_agent_wrapper
from agents.data_agent import DataAgent

# 创建智能体
data_agent = DataAgent()
wrapped_agent = create_camel_agent_wrapper(
    name="data_agent",
    agent_instance=data_agent,
    description="数据分析专家"
)

# 创建flow
flow = FlowFactory.create_flow(
    flow_type=FlowType.PLANNING,
    agents={"data_agent": wrapped_agent}
)

# 执行任务
result = await flow.execute("分析水质数据并生成报告")
```

### 2. 多智能体协作

```python
from agents.data_agent import DataAgent
from agents.mcp_toolcall_agent import MCPToolCallAgent

# 创建多个智能体
agents = {
    "data_agent": create_camel_agent_wrapper(
        "data_agent", DataAgent(), "数据分析专家"
    ),
    "mcp_agent": create_camel_agent_wrapper(
        "mcp_agent", MCPToolCallAgent(), "工具调用助手"
    )
}

# 创建协作flow
flow = FlowFactory.create_flow(
    flow_type=FlowType.PLANNING,
    agents=agents,
    primary_agent_key="data_agent"
)

# 执行协作任务
task = """
请完成以下任务:
1. [data_agent] 查询最新数据
2. [data_agent] 分析数据趋势
3. [mcp_agent] 生成报告
4. [mcp_agent] 发送通知
"""

result = await flow.execute(task)
```

### 3. 运行完整示例

#### 交互模式
```bash
python run_flow.py
```

#### 非交互模式
```bash
python run_flow.py --prompt "分析当前水质参数并提供优化建议"
```

#### 指定配置
```bash
python run_flow.py --collection "custom_knowledge_base" --max-steps 15
```

## 📚 详细文档

### Flow类型

目前支持的flow类型：

- **PLANNING**: 规划流程，自动分解任务并执行

### 智能体包装

将现有的Camel项目智能体包装为flow兼容格式：

```python
from flow.base import create_camel_agent_wrapper

wrapped_agent = create_camel_agent_wrapper(
    name="agent_name",           # 智能体名称
    agent_instance=agent_obj,    # 实际智能体实例
    description="agent功能描述"   # 智能体描述
)
```

### 规划工具API

PlanningTool提供完整的计划管理功能：

```python
from flow.planning_tool import PlanningTool

tool = PlanningTool()

# 创建计划
await tool.execute(
    command="create",
    plan_id="my_plan",
    title="数据分析计划",
    steps=["收集数据", "分析数据", "生成报告"]
)

# 更新步骤状态
await tool.execute(
    command="mark_step",
    plan_id="my_plan",
    step_index=0,
    step_status="completed"
)

# 获取计划详情
result = await tool.execute(command="get", plan_id="my_plan")
```

### 智能体选择策略

Flow系统会根据步骤类型智能选择执行器：

1. **明确指定**: `[agent_name]` 格式指定特定智能体
2. **关键词匹配**: 根据步骤内容匹配合适的智能体
3. **默认回退**: 使用主要智能体执行

关键词匹配规则：
- 包含"数据"、"分析"、"查询" → 选择data_agent
- 包含"工具"、"调用"、"mcp" → 选择mcp_agent

## 🔧 配置选项

### 环境变量

```bash
# API密钥 (必需)
OPENAI_API_KEY=your_openai_api_key
# 或
GPT_API_KEY=your_gpt_api_key
```

### Flow配置

```python
config = {
    "flow_type": "planning",
    "agents": agents_dict,
    "primary_agent_key": "data_agent",
    "plan_id": "custom_plan_id",
    "config": {
        "timeout": 3600,
        "max_iterations": 30
    }
}

flow = FlowFactory.create_flow_from_config(config)
```

### Agent配置

```python
agent_config = {
    "data_agent": {
        "system_prompt": "自定义系统提示",
        "max_steps": 10
    },
    "mcp_agent": {
        "max_steps": 15
    }
}
```

## 📊 执行状态

Flow系统实时跟踪执行状态：

- **[ ]** 未开始 (not_started)
- **[→]** 进行中 (in_progress)
- **[✓]** 已完成 (completed)
- **[!]** 阻塞 (blocked)

## 🎛️ 高级功能

### Flow注册表

管理多个流程实例：

```python
from flow.factory import flow_registry

# 注册flow
flow_registry.register_flow("daily_task", flow, config)

# 获取flow
flow = flow_registry.get_flow("daily_task")

# 列出所有flow
flows = flow_registry.list_flows()

# 清理资源
flow_registry.clear_all()
```

### 自定义执行器选择

重写executor选择逻辑：

```python
class CustomPlanningFlow(PlanningFlow):
    def get_executor(self, step_type: Optional[str] = None) -> Optional[BaseAgent]:
        # 自定义选择逻辑
        if step_type == "special_task":
            return self.get_agent("special_agent")
        return super().get_executor(step_type)
```

## 🔍 示例场景

### 1. 数据分析流程
```python
# 自动分解为: 数据收集 → 预处理 → 分析 → 可视化 → 报告
task = "对水产养殖数据进行全面分析并生成可视化报告"
```

### 2. 知识库问答
```python
# 自动分解为: 检索相关文档 → 理解问题 → 整合答案 → 验证准确性
task = "基于知识库回答：如何优化虾类养殖的溶氧管理？"
```

### 3. 综合任务处理
```python
# 自动分解为多个子任务，分配给不同智能体
task = """
处理水质异常报警:
1. 获取当前监测数据
2. 分析异常原因
3. 查找解决方案
4. 生成处理报告
5. 发送通知给相关人员
"""
```

## 🐛 故障排除

### 常见问题

1. **智能体初始化失败**
   - 检查API密钥配置
   - 确认依赖模块正确安装

2. **任务执行超时**
   - 增加timeout配置
   - 简化任务复杂度

3. **计划创建失败**
   - 检查任务描述是否清晰
   - 确认智能体可用性

### 调试模式

启用详细日志：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🤝 贡献指南

欢迎贡献代码和改进建议！

1. Fork项目
2. 创建特性分支
3. 提交更改
4. 发起Pull Request

## 📄 许可证

本项目采用MIT许可证，详见LICENSE文件。

---

💡 **提示**: Flow系统设计为渐进式增强，你可以从简单的单智能体开始，逐步扩展到复杂的多智能体协作场景。