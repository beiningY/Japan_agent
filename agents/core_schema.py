# agents/core_schema.py
# 定义Agent运行过程中所需的所有的核心数据类型，他不包含任何复杂的逻辑，他只是为了定义数据类型
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any


class AgentState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    FINISHED = "finished"
    ERROR = "error"


@dataclass
class Message:
    role: str
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    base64_image: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None

    @staticmethod
    def user(content: str) -> "Message":
        return Message(role="user", content=content)

    @staticmethod
    def system(content: str) -> "Message":
        return Message(role="system", content=content)

    @staticmethod
    def assistant(content: str) -> "Message":
        return Message(role="assistant", content=content)

    @staticmethod
    def tool(content: str, *, tool_call_id: Optional[str] = None, name: Optional[str] = None, base64_image: Optional[str] = None) -> "Message":
        return Message(role="tool", content=content, tool_call_id=tool_call_id, name=name, base64_image=base64_image)


@dataclass
class Memory:
    messages: List[Message] = field(default_factory=list)

    def add(self, message: Message) -> None:
        self.messages.append(message)


