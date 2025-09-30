# flow/planning_tool.py
"""
PlanningTool - 规划管理工具

提供计划创建、更新、状态跟踪等功能，适配Camel_agent项目
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Any
from enum import Enum
import time
import json
import logging

logger = logging.getLogger(__name__)


class PlanStepStatus(str, Enum):
    """计划步骤状态枚举"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"

    @classmethod
    def get_all_statuses(cls) -> List[str]:
        """获取所有状态值"""
        return [status.value for status in cls]

    @classmethod
    def get_active_statuses(cls) -> List[str]:
        """获取活动状态（未开始或进行中）"""
        return [cls.NOT_STARTED.value, cls.IN_PROGRESS.value]

    @classmethod
    def get_status_marks(cls) -> Dict[str, str]:
        """获取状态标记符号"""
        return {
            cls.COMPLETED.value: "[✓]",
            cls.IN_PROGRESS.value: "[→]",
            cls.BLOCKED.value: "[!]",
            cls.NOT_STARTED.value: "[ ]",
        }


@dataclass
class PlanningResult:
    """规划工具执行结果"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


@dataclass
class PlanningTool:
    """
    规划管理工具 - 提供计划创建、更新、状态跟踪功能

    适配Camel_agent项目，支持多智能体协作规划
    """

    name: str = "planning"
    description: str = "Plan creation and management tool for multi-agent collaboration"

    # 存储所有计划
    plans: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # 当前活动计划ID
    current_plan_id: Optional[str] = None

    def get_tool_schema(self) -> Dict[str, Any]:
        """获取工具的OpenAI function calling schema"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "enum": ["create", "update", "list", "get", "set_active", "mark_step", "delete"],
                            "description": "要执行的命令"
                        },
                        "plan_id": {
                            "type": "string",
                            "description": "计划ID"
                        },
                        "title": {
                            "type": "string",
                            "description": "计划标题"
                        },
                        "steps": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "计划步骤列表"
                        },
                        "step_index": {
                            "type": "integer",
                            "description": "步骤索引(从0开始)"
                        },
                        "step_status": {
                            "type": "string",
                            "enum": ["not_started", "in_progress", "completed", "blocked"],
                            "description": "步骤状态"
                        },
                        "step_notes": {
                            "type": "string",
                            "description": "步骤备注"
                        }
                    },
                    "required": ["command"]
                }
            }
        }

    async def execute(
        self,
        command: Literal["create", "update", "list", "get", "set_active", "mark_step", "delete"],
        plan_id: Optional[str] = None,
        title: Optional[str] = None,
        steps: Optional[List[str]] = None,
        step_index: Optional[int] = None,
        step_status: Optional[str] = None,
        step_notes: Optional[str] = None,
        **kwargs
    ) -> PlanningResult:
        """执行规划工具命令"""

        try:
            if command == "create":
                return await self._create_plan(plan_id, title, steps)
            elif command == "update":
                return await self._update_plan(plan_id, title, steps)
            elif command == "list":
                return await self._list_plans()
            elif command == "get":
                return await self._get_plan(plan_id)
            elif command == "set_active":
                return await self._set_active_plan(plan_id)
            elif command == "mark_step":
                return await self._mark_step(plan_id, step_index, step_status, step_notes)
            elif command == "delete":
                return await self._delete_plan(plan_id)
            else:
                return PlanningResult(
                    success=False,
                    message=f"未知命令: {command}"
                )
        except Exception as e:
            logger.error(f"执行规划工具命令失败: {e}")
            return PlanningResult(
                success=False,
                message=f"执行失败: {str(e)}"
            )

    async def _create_plan(
        self,
        plan_id: Optional[str],
        title: Optional[str],
        steps: Optional[List[str]]
    ) -> PlanningResult:
        """创建新计划"""

        if not plan_id:
            plan_id = f"plan_{int(time.time())}"

        if plan_id in self.plans:
            return PlanningResult(
                success=False,
                message=f"计划 {plan_id} 已存在"
            )

        if not title:
            return PlanningResult(
                success=False,
                message="计划标题不能为空"
            )

        if not steps or not isinstance(steps, list):
            return PlanningResult(
                success=False,
                message="计划步骤必须是非空列表"
            )

        # 创建计划
        plan = {
            "plan_id": plan_id,
            "title": title,
            "steps": steps,
            "step_statuses": [PlanStepStatus.NOT_STARTED.value] * len(steps),
            "step_notes": [""] * len(steps),
            "created_at": time.time(),
            "updated_at": time.time()
        }

        self.plans[plan_id] = plan
        self.current_plan_id = plan_id

        return PlanningResult(
            success=True,
            message=f"计划 {plan_id} 创建成功",
            data={"plan": plan, "formatted": self._format_plan(plan)}
        )

    async def _update_plan(
        self,
        plan_id: Optional[str],
        title: Optional[str],
        steps: Optional[List[str]]
    ) -> PlanningResult:
        """更新计划"""

        if not plan_id:
            return PlanningResult(
                success=False,
                message="必须指定计划ID"
            )

        if plan_id not in self.plans:
            return PlanningResult(
                success=False,
                message=f"计划 {plan_id} 不存在"
            )

        plan = self.plans[plan_id]

        # 更新标题
        if title:
            plan["title"] = title

        # 更新步骤
        if steps:
            old_steps = plan["steps"]
            old_statuses = plan["step_statuses"]
            old_notes = plan["step_notes"]

            # 保持已有步骤的状态
            new_statuses = []
            new_notes = []

            for i, step in enumerate(steps):
                if i < len(old_steps) and step == old_steps[i]:
                    # 步骤未变，保持原状态
                    new_statuses.append(old_statuses[i] if i < len(old_statuses) else PlanStepStatus.NOT_STARTED.value)
                    new_notes.append(old_notes[i] if i < len(old_notes) else "")
                else:
                    # 新步骤或修改的步骤
                    new_statuses.append(PlanStepStatus.NOT_STARTED.value)
                    new_notes.append("")

            plan["steps"] = steps
            plan["step_statuses"] = new_statuses
            plan["step_notes"] = new_notes

        plan["updated_at"] = time.time()

        return PlanningResult(
            success=True,
            message=f"计划 {plan_id} 更新成功",
            data={"plan": plan, "formatted": self._format_plan(plan)}
        )

    async def _list_plans(self) -> PlanningResult:
        """列出所有计划"""

        if not self.plans:
            return PlanningResult(
                success=True,
                message="暂无计划",
                data={"plans": []}
            )

        plans_info = []
        for plan_id, plan in self.plans.items():
            completed = sum(1 for status in plan["step_statuses"] if status == PlanStepStatus.COMPLETED.value)
            total = len(plan["steps"])
            is_current = plan_id == self.current_plan_id

            plans_info.append({
                "plan_id": plan_id,
                "title": plan["title"],
                "progress": f"{completed}/{total}",
                "is_current": is_current
            })

        return PlanningResult(
            success=True,
            message=f"共有 {len(self.plans)} 个计划",
            data={"plans": plans_info}
        )

    async def _get_plan(self, plan_id: Optional[str]) -> PlanningResult:
        """获取计划详情"""

        if not plan_id:
            plan_id = self.current_plan_id

        if not plan_id:
            return PlanningResult(
                success=False,
                message="未指定计划ID且无当前活动计划"
            )

        if plan_id not in self.plans:
            return PlanningResult(
                success=False,
                message=f"计划 {plan_id} 不存在"
            )

        plan = self.plans[plan_id]
        formatted = self._format_plan(plan)

        return PlanningResult(
            success=True,
            message="获取计划成功",
            data={"plan": plan, "formatted": formatted}
        )

    async def _set_active_plan(self, plan_id: Optional[str]) -> PlanningResult:
        """设置当前活动计划"""

        if not plan_id:
            return PlanningResult(
                success=False,
                message="必须指定计划ID"
            )

        if plan_id not in self.plans:
            return PlanningResult(
                success=False,
                message=f"计划 {plan_id} 不存在"
            )

        self.current_plan_id = plan_id

        return PlanningResult(
            success=True,
            message=f"已设置 {plan_id} 为当前活动计划"
        )

    async def _mark_step(
        self,
        plan_id: Optional[str],
        step_index: Optional[int],
        step_status: Optional[str],
        step_notes: Optional[str]
    ) -> PlanningResult:
        """标记步骤状态"""

        if not plan_id:
            plan_id = self.current_plan_id

        if not plan_id:
            return PlanningResult(
                success=False,
                message="未指定计划ID且无当前活动计划"
            )

        if plan_id not in self.plans:
            return PlanningResult(
                success=False,
                message=f"计划 {plan_id} 不存在"
            )

        if step_index is None:
            return PlanningResult(
                success=False,
                message="必须指定步骤索引"
            )

        plan = self.plans[plan_id]

        if step_index < 0 or step_index >= len(plan["steps"]):
            return PlanningResult(
                success=False,
                message=f"步骤索引 {step_index} 超出范围 [0, {len(plan['steps'])-1}]"
            )

        # 更新状态
        if step_status and step_status in PlanStepStatus.get_all_statuses():
            plan["step_statuses"][step_index] = step_status

        # 更新备注
        if step_notes is not None:
            plan["step_notes"][step_index] = step_notes

        plan["updated_at"] = time.time()

        return PlanningResult(
            success=True,
            message=f"步骤 {step_index} 状态已更新",
            data={"plan": plan, "formatted": self._format_plan(plan)}
        )

    async def _delete_plan(self, plan_id: Optional[str]) -> PlanningResult:
        """删除计划"""

        if not plan_id:
            return PlanningResult(
                success=False,
                message="必须指定计划ID"
            )

        if plan_id not in self.plans:
            return PlanningResult(
                success=False,
                message=f"计划 {plan_id} 不存在"
            )

        del self.plans[plan_id]

        # 如果删除的是当前计划，清空当前计划ID
        if self.current_plan_id == plan_id:
            self.current_plan_id = None

        return PlanningResult(
            success=True,
            message=f"计划 {plan_id} 已删除"
        )

    def _format_plan(self, plan: Dict[str, Any]) -> str:
        """格式化计划输出"""

        plan_id = plan["plan_id"]
        title = plan["title"]
        steps = plan["steps"]
        step_statuses = plan["step_statuses"]
        step_notes = plan["step_notes"]

        # 统计进度
        total_steps = len(steps)
        completed = sum(1 for status in step_statuses if status == PlanStepStatus.COMPLETED.value)
        in_progress = sum(1 for status in step_statuses if status == PlanStepStatus.IN_PROGRESS.value)
        blocked = sum(1 for status in step_statuses if status == PlanStepStatus.BLOCKED.value)
        not_started = sum(1 for status in step_statuses if status == PlanStepStatus.NOT_STARTED.value)

        progress_pct = (completed / total_steps * 100) if total_steps > 0 else 0

        # 构建输出
        output = f"计划: {title} (ID: {plan_id})\n"
        output += "=" * len(output) + "\n\n"

        output += f"进度: {completed}/{total_steps} 步骤已完成 ({progress_pct:.1f}%)\n"
        output += f"状态: {completed} 已完成, {in_progress} 进行中, {blocked} 阻塞, {not_started} 未开始\n\n"
        output += "步骤:\n"

        status_marks = PlanStepStatus.get_status_marks()

        for i, (step, status, notes) in enumerate(zip(steps, step_statuses, step_notes)):
            status_mark = status_marks.get(status, status_marks[PlanStepStatus.NOT_STARTED.value])
            output += f"{i}. {status_mark} {step}\n"
            if notes:
                output += f"   备注: {notes}\n"

        return output

    def get_current_step_info(self) -> tuple[Optional[int], Optional[Dict[str, Any]]]:
        """获取当前需要执行的步骤信息"""

        if not self.current_plan_id or self.current_plan_id not in self.plans:
            return None, None

        plan = self.plans[self.current_plan_id]
        steps = plan["steps"]
        step_statuses = plan["step_statuses"]

        # 查找第一个未完成的步骤
        for i, step in enumerate(steps):
            if i >= len(step_statuses):
                status = PlanStepStatus.NOT_STARTED.value
            else:
                status = step_statuses[i]

            if status in PlanStepStatus.get_active_statuses():
                step_info = {
                    "text": step,
                    "status": status,
                    "index": i
                }

                # 尝试从步骤文本中提取类型信息
                import re
                type_match = re.search(r"\[([A-Za-z_\u4e00-\u9fff]+)\]", step)
                if type_match:
                    step_info["type"] = type_match.group(1).lower()

                return i, step_info

        return None, None