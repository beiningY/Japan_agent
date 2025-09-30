from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from .core_base import CoreBaseAgent


class ReActAgent(CoreBaseAgent, ABC):
    """ReAct 抽象层：定义 think/act/step 模式。

    子类实现 think() 判定是否需要执行动作；实现 act() 执行动作。
    """

    # LLM 依赖由具体实现类自行管理（以避免与现有 openai/camel 代码冲突）
    llm: Optional[object] = None

    max_steps: int = 10

    @abstractmethod
    async def think(self) -> bool:
        """分析当前状态，决定是否需要执行动作。"""

    @abstractmethod
    async def act(self) -> str:
        """执行动作并返回本步结果文本。"""

    async def step(self) -> str:
        should_act = await self.think()
        if not should_act:
            # 如果已完成，返回最终助手回答内容（而不是固定提示），便于上层输出最终答案
            if getattr(self, "state", None) and getattr(self, "messages", None):
                try:
                    # 查找最后一条 assistant 消息，但排除工具调用的JSON结果
                    for m in reversed(self.messages):
                        if m.role == "assistant" and m.content:
                            content = m.content.strip()
                            # 检查是否是工具调用的JSON结果或特殊标记
                            if content in ("[tools_executed]", "[tools] executing"):
                                continue
                            try:
                                import json
                                parsed = json.loads(content)
                                if isinstance(parsed, dict) and "chunks" in parsed:
                                    continue  # 跳过工具调用结果
                            except (json.JSONDecodeError, TypeError):
                                pass
                            return content
                except Exception:
                    pass
            return "Thinking complete - no action needed"

        action_result = await self.act()

        # 如果act()返回特殊标记，表示需要继续让LLM生成回答
        if action_result == "[tools_executed]":
            return "[tools_executed]"

        return action_result


