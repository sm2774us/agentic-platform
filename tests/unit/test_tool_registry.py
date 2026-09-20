import pytest

from agentic_platform.tools.registry import (
    HumanApprovalRequiredError,
    Tool,
    ToolNotFoundError,
    ToolRegistry,
    default_tool_registry,
)


def test_register_and_invoke_tool() -> None:
    registry = ToolRegistry()
    registry.register(Tool("echo", "echoes input", lambda value: value))
    result = registry.invoke("echo", value="hi")
    assert result.output == "hi"
    assert registry.audit_log[-1]["status"] == "executed"


def test_duplicate_registration_raises() -> None:
    registry = ToolRegistry()
    registry.register(Tool("echo", "d", lambda: None))
    with pytest.raises(ValueError, match="already registered"):
        registry.register(Tool("echo", "d", lambda: None))


def test_invoke_unknown_tool_raises() -> None:
    registry = ToolRegistry()
    with pytest.raises(ToolNotFoundError):
        registry.invoke("missing")


def test_sensitive_tool_blocked_without_approval() -> None:
    registry = default_tool_registry()
    with pytest.raises(HumanApprovalRequiredError):
        registry.invoke("apply_schema_migration", migration_id="001")
    assert registry.audit_log[-1]["status"] == "blocked_pending_review"


def test_sensitive_tool_allowed_with_approval() -> None:
    registry = default_tool_registry()
    result = registry.invoke("apply_schema_migration", migration_id="001", human_approved=True)
    assert result.output == "migration:001:applied"
    assert result.requires_review is True


def test_default_registry_search_and_calculate() -> None:
    registry = default_tool_registry()
    search = registry.invoke("search_knowledge_base", query="refund policy")
    assert "refund_policy" in search.output[0]
    calc = registry.invoke("calculate", expression="2*(3+4)")
    assert calc.output == 14.0


def test_calculate_rejects_unsafe_expression() -> None:
    registry = default_tool_registry()
    with pytest.raises(ValueError, match="Unsupported characters"):
        registry.invoke("calculate", expression="__import__('os')")


def test_registry_names_lists_registered_tools() -> None:
    registry = default_tool_registry()
    assert "calculate" in registry.names()
    assert "search_knowledge_base" in registry.names()
