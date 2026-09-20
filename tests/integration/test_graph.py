import pytest

from agentic_platform.agents.graph import GraphExecutionError, build_research_writer_graph
from agentic_platform.agents.state import AgentState
from agentic_platform.config.settings import Settings
from agentic_platform.orchestration.llm_client import MockLLMClient
from agentic_platform.rag.pipeline import Chunk, HybridRetriever
from agentic_platform.tools.registry import default_tool_registry


def _build_graph(max_turns: int = 3):
    settings = Settings(max_agent_turns=max_turns)
    llm = MockLLMClient(settings, canned_responses={"refund": "Refunds take five business days."})
    retriever = HybridRetriever()
    retriever.index([Chunk("d1", "d1::0", "refund policy is five business days", "kb")])
    tools = default_tool_registry()
    return build_research_writer_graph(
        llm=llm, retriever=retriever, tools=tools, max_turns=max_turns
    )


def test_graph_runs_to_completion_and_grounds_answer() -> None:
    graph = _build_graph()
    result = graph.run(AgentState(task="refund policy"))
    assert result.final_answer is not None
    assert result.requires_human_review is False
    assert any(m.content for m in result.messages)


def test_graph_raises_on_unknown_node() -> None:
    graph = _build_graph()
    graph.nodes.pop("writer")
    with pytest.raises(GraphExecutionError, match="Unknown node"):
        graph.run(AgentState(task="refund policy"))


def test_graph_raises_on_max_steps_exceeded() -> None:
    graph = _build_graph(max_turns=1)
    graph.max_steps = 1
    with pytest.raises(GraphExecutionError, match="max_steps"):
        graph.run(AgentState(task="refund policy"))


def test_graph_terminates_when_turn_count_exceeds_max_turns() -> None:
    graph = _build_graph(max_turns=1)

    def bump(state: AgentState) -> AgentState:
        state.turn_count = 99
        return state

    graph.nodes["supervisor"] = bump
    result = graph.run(AgentState(task="x"))
    assert result.turn_count == 99


def test_graph_handles_blocked_tool_call() -> None:
    from agentic_platform.tools.registry import Tool, ToolRegistry

    settings = Settings(max_agent_turns=3)
    llm = MockLLMClient(settings)
    retriever = HybridRetriever()
    retriever.index([Chunk("d1", "d1::0", "some context", "kb")])
    tools = ToolRegistry()
    tools.register(
        Tool("search_knowledge_base", "sensitive variant", lambda query: [query], sensitive=True)
    )
    graph = build_research_writer_graph(llm=llm, retriever=retriever, tools=tools, max_turns=3)

    result = graph.run(AgentState(task="anything"))

    assert result.errors
    assert "requires human approval" in result.errors[0]
