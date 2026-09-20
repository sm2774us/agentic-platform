"""Shared state contract passed between nodes in the agent graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class AgentRole(StrEnum):
    SUPERVISOR = "supervisor"
    RESEARCHER = "researcher"
    ANALYST = "analyst"
    WRITER = "writer"
    REVIEWER = "reviewer"


@dataclass(slots=True)
class Message:
    role: AgentRole | str
    content: str


@dataclass(slots=True)
class AgentState:
    task: str
    messages: list[Message] = field(default_factory=list)
    retrieved_context: list[str] = field(default_factory=list)
    tool_outputs: list[str] = field(default_factory=list)
    draft: str | None = None
    final_answer: str | None = None
    turn_count: int = 0
    next_node: str | None = None
    requires_human_review: bool = False
    errors: list[str] = field(default_factory=list)

    def add(self, role: AgentRole | str, content: str) -> None:
        self.messages.append(Message(role=role, content=content))
