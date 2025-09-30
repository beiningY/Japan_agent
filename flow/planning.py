# flow/planning.py
"""
PlanningFlow - 规划执行流程

实现多智能体协作的规划执行逻辑，适配Camel_agent项目
"""

from __future__ import annotations
import asyncio
import time
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from agents.core_schema import AgentState, Message
from .base import BaseFlow, BaseAgent
from .planning_tool import PlanningTool, PlanStepStatus

logger = logging.getLogger(__name__)


@dataclass
class PlanningFlow(BaseFlow):
    """
    规划执行流程 - 支持多智能体协作的任务规划和执行

    基于OpenManus设计，适配Camel_agent项目特点
    """

    planning_tool: PlanningTool = field(default_factory=PlanningTool)
    active_plan_id: str = field(default_factory=lambda: f"plan_{int(time.time())}")
    current_step_index: Optional[int] = None
    llm_client: Optional[Any] = None  # 用于LLM调用的客户端

    async def execute(self, input_text: str) -> str:
        """执行规划流程"""

        try:
            if not self.primary_agent:
                raise ValueError("未找到主要执行agent")

            # 创建初始计划
            if input_text:
                await self._create_initial_plan(input_text)

                # 验证计划创建成功
                if self.active_plan_id not in self.planning_tool.plans:
                    logger.error(f"计划创建失败，计划ID {self.active_plan_id} 不存在")
                    return f"为请求创建计划失败: {input_text}"

            result = ""
            max_iterations = 20  # 防止无限循环
            iteration = 0

            while iteration < max_iterations:
                iteration += 1

                # 获取当前要执行的步骤
                self.current_step_index, step_info = self.planning_tool.get_current_step_info()

                # 如果没有更多步骤，完成计划
                if self.current_step_index is None:
                    result += await self._finalize_plan()
                    break

                # 执行当前步骤
                step_type = step_info.get("type") if step_info else None
                executor = self.get_executor(step_type)

                if not executor:
                    logger.error(f"未找到合适的执行器处理步骤类型: {step_type}")
                    await self._mark_step_blocked(f"未找到合适的执行器")
                    continue

                step_result = await self._execute_step(executor, step_info)
                result += step_result + "\n"

                # 检查agent是否请求终止
                if hasattr(executor, "state") and executor.state == AgentState.FINISHED:
                    break

            if iteration >= max_iterations:
                result += "\n⚠️ 达到最大迭代次数限制，流程终止\n"

            return result

        except Exception as e:
            logger.error(f"PlanningFlow执行错误: {str(e)}")
            return f"执行失败: {str(e)}"

    async def _create_initial_plan(self, request: str) -> None:
        """基于请求创建初始计划"""

        logger.info(f"创建初始计划，ID: {self.active_plan_id}")

        # 构建agent描述信息
        agents_description = []
        for key, agent in self.agents.items():
            agents_description.append({
                "name": key,
                "description": agent.description or f"{key} agent"
            })

        # 创建计划提示
        system_prompt = (
            "你是一个规划助手。请为给定的任务创建一个清晰、可执行的计划。"
            "计划应该包含具体的步骤，每个步骤都应该是可操作的。"
            "优先考虑关键里程碑而不是详细的子步骤。"
        )

        if len(agents_description) > 1:
            system_prompt += (
                f"\n当前可用的智能体: {json.dumps(agents_description, ensure_ascii=False)}\n"
                "在创建步骤时，可以使用格式 '[agent_name]' 来指定特定的智能体执行该步骤。"
                "例如: '[data_agent] 分析数据' 或 '[mcp_agent] 执行工具调用'"
            )

        # 使用主agent创建计划
        planning_prompt = (
            f"{system_prompt}\n\n"
            f"请为以下任务创建详细的执行计划: {request}\n\n"
            "请返回一个包含以下结构的JSON:\n"
            "{\n"
            '  "title": "计划标题",\n'
            '  "steps": ["步骤1", "步骤2", "步骤3"]\n'
            "}"
        )

        try:
            # 调用主agent生成计划
            response = await self.primary_agent.run(planning_prompt)

            # 尝试解析JSON响应
            plan_data = self._extract_plan_from_response(response, request)

            # 创建计划
            result = await self.planning_tool.execute(
                command="create",
                plan_id=self.active_plan_id,
                title=plan_data["title"],
                steps=plan_data["steps"]
            )

            if result.success:
                logger.info(f"计划创建成功: {result.message}")
            else:
                logger.error(f"计划创建失败: {result.message}")
                raise RuntimeError(result.message)

        except Exception as e:
            logger.warning(f"使用agent创建计划失败: {e}，创建默认计划")
            await self._create_default_plan(request)

    def _extract_plan_from_response(self, response: str, request: str) -> Dict[str, Any]:
        """从agent响应中提取计划数据"""

        try:
            # 尝试找到JSON部分
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                plan_data = json.loads(json_str)

                if "title" in plan_data and "steps" in plan_data:
                    return plan_data

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"解析计划JSON失败: {e}")

        # 如果JSON解析失败，尝试从文本中提取步骤
        lines = response.split('\n')
        steps = []
        for line in lines:
            line = line.strip()
            if line and (line.startswith('1.') or line.startswith('-') or line.startswith('•')):
                # 清理步骤文本
                step = re.sub(r'^[\d\.\-\•\s]+', '', line).strip()
                if step:
                    steps.append(step)

        if not steps:
            # 生成默认步骤
            steps = [
                "分析任务需求",
                "制定执行策略",
                "执行主要任务",
                "验证结果"
            ]

        return {
            "title": f"任务计划: {request[:30]}{'...' if len(request) > 30 else ''}",
            "steps": steps
        }

    async def _create_default_plan(self, request: str) -> None:
        """创建默认计划"""

        default_steps = [
            "分析任务需求和目标",
            "收集必要的数据和信息",
            "执行主要任务操作",
            "验证和总结结果"
        ]

        result = await self.planning_tool.execute(
            command="create",
            plan_id=self.active_plan_id,
            title=f"任务计划: {request[:50]}{'...' if len(request) > 50 else ''}",
            steps=default_steps
        )

        if not result.success:
            raise RuntimeError(f"创建默认计划失败: {result.message}")

    async def _execute_step(self, executor: BaseAgent, step_info: Dict[str, Any]) -> str:
        """执行当前步骤"""

        # 首先标记步骤为进行中
        await self._mark_step_in_progress()

        # 获取计划状态
        plan_result = await self.planning_tool.execute(command="get", plan_id=self.active_plan_id)
        plan_status = plan_result.data["formatted"] if plan_result.success else "无法获取计划状态"

        step_text = step_info.get("text", f"步骤 {self.current_step_index}")

        # 为agent创建执行提示
        step_prompt = f"""
当前计划状态:
{plan_status}

当前任务:
你正在执行步骤 {self.current_step_index}: "{step_text}"

请只执行这个当前步骤，使用适当的工具。完成后，请提供执行结果的总结。
"""

        try:
            # 执行步骤
            step_result = await executor.run(step_prompt)

            # 标记步骤为完成
            await self._mark_step_completed()

            return f"✅ 步骤 {self.current_step_index} 完成: {step_text}\n结果: {step_result}"

        except Exception as e:
            # 标记步骤为阻塞
            await self._mark_step_blocked(f"执行错误: {str(e)}")
            logger.error(f"执行步骤 {self.current_step_index} 失败: {e}")
            return f"❌ 步骤 {self.current_step_index} 失败: {step_text}\n错误: {str(e)}"

    async def _mark_step_in_progress(self) -> None:
        """标记当前步骤为进行中"""
        if self.current_step_index is not None:
            await self.planning_tool.execute(
                command="mark_step",
                plan_id=self.active_plan_id,
                step_index=self.current_step_index,
                step_status=PlanStepStatus.IN_PROGRESS.value
            )

    async def _mark_step_completed(self) -> None:
        """标记当前步骤为完成"""
        if self.current_step_index is not None:
            result = await self.planning_tool.execute(
                command="mark_step",
                plan_id=self.active_plan_id,
                step_index=self.current_step_index,
                step_status=PlanStepStatus.COMPLETED.value
            )
            if result.success:
                logger.info(f"步骤 {self.current_step_index} 已标记为完成")

    async def _mark_step_blocked(self, reason: str) -> None:
        """标记当前步骤为阻塞"""
        if self.current_step_index is not None:
            await self.planning_tool.execute(
                command="mark_step",
                plan_id=self.active_plan_id,
                step_index=self.current_step_index,
                step_status=PlanStepStatus.BLOCKED.value,
                step_notes=reason
            )

    async def _finalize_plan(self) -> str:
        """完成计划并生成总结"""

        # 获取最终计划状态
        plan_result = await self.planning_tool.execute(command="get", plan_id=self.active_plan_id)

        if plan_result.success:
            plan_status = plan_result.data["formatted"]

            # 生成总结
            try:
                summary_prompt = f"""
计划已完成。以下是最终的计划状态:

{plan_status}

请为这个已完成的计划提供简洁的总结，包括:
1. 完成了哪些主要任务
2. 取得了什么成果
3. 如有需要，提出后续建议
"""
                if self.primary_agent:
                    summary = await self.primary_agent.run(summary_prompt)
                    return f"🎉 计划执行完成!\n\n总结:\n{summary}\n\n详细状态:\n{plan_status}"
                else:
                    return f"🎉 计划执行完成!\n\n{plan_status}"

            except Exception as e:
                logger.error(f"生成计划总结失败: {e}")
                return f"🎉 计划执行完成!\n\n{plan_status}"
        else:
            return "计划执行完成，但无法获取详细状态。"

    def get_executor(self, step_type: Optional[str] = None) -> Optional[BaseAgent]:
        """
        根据步骤类型选择合适的执行器
        扩展了基类的逻辑，增加了更多智能匹配
        """

        # 如果明确指定了agent类型
        if step_type and step_type in self.agents:
            return self.agents[step_type]

        # 根据步骤类型关键词匹配agent
        if step_type:
            step_type_lower = step_type.lower()

            # 数据相关任务
            if any(keyword in step_type_lower for keyword in ["data", "数据", "分析", "查询", "检索"]):
                data_agent = self.get_agent("data_agent")
                if data_agent:
                    return data_agent

            # 工具调用任务
            if any(keyword in step_type_lower for keyword in ["tool", "工具", "调用", "mcp"]):
                mcp_agent = self.get_agent("mcp_agent")
                if mcp_agent:
                    return mcp_agent

        # 使用父类的默认逻辑
        return super().get_executor(step_type)