# agents/core_base.py
from __future__ import annotations
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import List, Optional
from .core_schema import AgentState, Memory, Message


class CoreBaseAgent(ABC):
    """更通用的基础 Agent：提供状态管理、内存、主循环。
    """

    # 基本属性（子类可覆盖）
    name: str = "agent"
    description: Optional[str] = None

    # 提示词
    system_prompt: Optional[str] = None
    next_step_prompt: Optional[str] = None

    # 依赖
    memory: Memory
    state: AgentState

    # 控制
    max_steps: int = 10
    current_step: int = 0
    duplicate_threshold: int = 2

    def __init__(self, *, system_prompt: Optional[str] = None, next_step_prompt: Optional[str] = None, max_steps: Optional[int] = None) -> None:
        self.system_prompt = system_prompt or self.system_prompt
        self.next_step_prompt = next_step_prompt or self.next_step_prompt
        if max_steps is not None:
            self.max_steps = max_steps
        self.memory = Memory()
        self.state = AgentState.IDLE

    @asynccontextmanager
    async def state_context(self, new_state: AgentState):
        if not isinstance(new_state, AgentState):
            raise ValueError(f"Invalid state: {new_state}")
        prev = self.state
        self.state = new_state
        try:
            yield
        except Exception:
            self.state = AgentState.ERROR
            raise
        finally:
            if self.state != AgentState.ERROR:
                self.state = prev

    def add_message(self, message: Message) -> None:
        self.memory.add(message)

    def update_memory(self, role: str, content: str, *, base64_image: Optional[str] = None, **kwargs) -> None:
        if role == "user":
            self.add_message(Message.user(content))
        elif role == "system":
            self.add_message(Message.system(content))
        elif role == "assistant":
            self.add_message(Message.assistant(content))
        elif role == "tool":
            self.add_message(Message.tool(content, tool_call_id=kwargs.get("tool_call_id"), name=kwargs.get("name"), base64_image=base64_image))
        else:
            raise ValueError(f"Unsupported role: {role}")

    @property
    def messages(self) -> List[Message]:
        return self.memory.messages

    @messages.setter
    def messages(self, value: List[Message]):
        self.memory.messages = value

    async def run(self, request: Optional[str] = None) -> str:
        if self.state != AgentState.IDLE:
            raise RuntimeError(f"Cannot run agent from state: {self.state}")

        if request:
            self.update_memory("user", request)
        if self.system_prompt:
            # 将系统消息置于记忆前置位置（保持顺序：system 在最前）
            self.memory.messages = [Message.system(self.system_prompt)] + self.memory.messages

        results: List[str] = []
        async with self.state_context(AgentState.RUNNING):
            while self.current_step < self.max_steps and self.state != AgentState.FINISHED:
                self.current_step += 1
                step_result = await self.step()
                results.append(f"Step {self.current_step}: {step_result}")
                if self.is_stuck():
                    self.handle_stuck_state()
            if self.current_step >= self.max_steps and self.state != AgentState.FINISHED:
                results.append(f"Terminated: Reached max steps ({self.max_steps})")
        # 复位，便于复用
        self.current_step = 0
        self.state = AgentState.IDLE
        return "\n".join(results) if results else "No steps executed"

    # 子类需要实现的核心一步
    @abstractmethod
    async def step(self) -> str:
        ...

    def is_stuck(self) -> bool:
        if len(self.memory.messages) < 2:
            return False
        last = self.memory.messages[-1]
        if last.role != "assistant" or not last.content:
            return False
        duplicate_count = 0
        for msg in reversed(self.memory.messages[:-1]):
            if msg.role == "assistant" and msg.content == last.content:
                duplicate_count += 1
                if duplicate_count >= self.duplicate_threshold:
                    return True
            else:
                break
        return False

    def handle_stuck_state(self) -> None:
        stuck_prompt = (
            "Observed duplicate responses. Consider new strategies and avoid repeating "
            "ineffective paths already attempted."
        )
        self.next_step_prompt = f"{stuck_prompt}\n{self.next_step_prompt or ''}".strip()


