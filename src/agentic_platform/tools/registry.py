"""Tool-integrated reasoning: a typed, auditable tool registry."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from agentic_platform.observability.tracing import traced_span


class ToolNotFoundError(KeyError):
    pass


class HumanApprovalRequiredError(RuntimeError):
    pass


@dataclass(slots=True)
class ToolResult:
    tool_name: str
    output: Any
    requires_review: bool = False


@dataclass(slots=True)
class Tool:
    name: str
    description: str
    handler: Callable[..., Any]
    sensitive: bool = False


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
        self._audit_log: list[dict[str, Any]] = []

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool {tool.name!r} already registered")
        self._tools[tool.name] = tool

    def names(self) -> tuple[str, ...]:
        return tuple(self._tools)

    @property
    def audit_log(self) -> tuple[dict[str, Any], ...]:
        return tuple(self._audit_log)

    def invoke(self, name: str, *, human_approved: bool = False, **kwargs: Any) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            raise ToolNotFoundError(name)

        with traced_span("tool.invoke", tool=name, sensitive=tool.sensitive) as span:
            if tool.sensitive and not human_approved:
                self._audit_log.append(
                    {"tool": name, "args": kwargs, "status": "blocked_pending_review"}
                )
                span.attributes["blocked"] = True
                raise HumanApprovalRequiredError(
                    f"Tool {name!r} is sensitive and requires human approval"
                )

            output = tool.handler(**kwargs)
            self._audit_log.append({"tool": name, "args": kwargs, "status": "executed"})
            return ToolResult(tool_name=name, output=output, requires_review=tool.sensitive)


def default_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()

    def search_knowledge_base(query: str) -> list[str]:
        return [f"doc:{query.lower().replace(' ', '_')}::relevant_passage"]

    def calculate(expression: str) -> float:
        allowed = set("0123456789+-*/(). ")
        if not set(expression) <= allowed:
            raise ValueError("Unsupported characters in expression")
        return float(eval(expression, {"__builtins__": {}}, {}))

    def apply_schema_migration(migration_id: str) -> str:
        return f"migration:{migration_id}:applied"

    registry.register(
        Tool(
            "search_knowledge_base", "Semantic search over the vector store", search_knowledge_base
        )
    )
    registry.register(Tool("calculate", "Evaluate a numeric expression", calculate))
    registry.register(
        Tool(
            "apply_schema_migration",
            "Apply a database schema migration",
            apply_schema_migration,
            sensitive=True,
        )
    )
    return registry
