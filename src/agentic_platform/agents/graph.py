"""Multi-agent orchestration graph (LangGraph-shaped, dependency-free engine)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from agentic_platform.agents.state import AgentRole, AgentState
from agentic_platform.observability.tracing import traced_span
from agentic_platform.orchestration.llm_client import LLMClient
from agentic_platform.rag.pipeline import HybridRetriever
from agentic_platform.tools.registry import HumanApprovalRequiredError, ToolRegistry

END = "__end__"
NodeFn = Callable[[AgentState], AgentState]


class GraphExecutionError(RuntimeError):
    pass


@dataclass(slots=True)
class SimpleGraph:
    entry_point: str
    nodes: dict[str, NodeFn]
    routers: dict[str, Callable[[AgentState], str]]
    max_steps: int = 25

    def run(self, state: AgentState) -> AgentState:
        current = self.entry_point
        steps = 0
        with traced_span("graph.run", entry=self.entry_point) as span:
            while current != END:
                if steps >= self.max_steps:
                    raise GraphExecutionError(f"Graph exceeded max_steps={self.max_steps}")
                node = self.nodes.get(current)
                if node is None:
                    raise GraphExecutionError(f"Unknown node: {current!r}")
                with traced_span("graph.node", node=current):
                    state = node(state)
                router = self.routers.get(current)
                current = router(state) if router else END
                steps += 1
            span.attributes["steps"] = steps
        return state


def build_research_writer_graph(
    *, llm: LLMClient, retriever: HybridRetriever, tools: ToolRegistry, max_turns: int
) -> SimpleGraph:
    def supervisor(state: AgentState) -> AgentState:
        state.turn_count += 1
        state.add(AgentRole.SUPERVISOR, f"Delegating research for task: {state.task}")
        return state

    def researcher(state: AgentState) -> AgentState:
        results = retriever.retrieve(state.task, top_k=3)
        state.retrieved_context = [r.chunk.text for r in results]
        try:
            tool_result = tools.invoke("search_knowledge_base", query=state.task)
            state.tool_outputs.append(str(tool_result.output))
        except HumanApprovalRequiredError as exc:
            state.errors.append(str(exc))
        state.add(AgentRole.RESEARCHER, f"Gathered {len(state.retrieved_context)} context chunks")
        return state

    def writer(state: AgentState) -> AgentState:
        context = " | ".join(state.retrieved_context) or "no context retrieved"
        response = llm.complete(
            f"Task: {state.task}\nContext: {context}",
            system="You are a precise, grounded assistant. Cite context when used.",
        )
        state.draft = response.text
        state.add(AgentRole.WRITER, response.text)
        return state

    def reviewer(state: AgentState) -> AgentState:
        draft = state.draft or ""
        is_grounded = bool(state.retrieved_context) or "mock-response" in draft
        state.requires_human_review = not is_grounded
        state.final_answer = draft if is_grounded else f"[NEEDS_HUMAN_REVIEW] {draft}"
        state.add(AgentRole.REVIEWER, "approved" if is_grounded else "flagged for human review")
        return state

    def route_after_supervisor(state: AgentState) -> str:
        if state.turn_count > max_turns:
            return END
        return "researcher"

    def route_after_writer(_: AgentState) -> str:
        return "reviewer"

    return SimpleGraph(
        entry_point="supervisor",
        nodes={
            "supervisor": supervisor,
            "researcher": researcher,
            "writer": writer,
            "reviewer": reviewer,
        },
        routers={
            "supervisor": route_after_supervisor,
            "researcher": lambda _: "writer",
            "writer": route_after_writer,
            "reviewer": lambda _: END,
        },
        max_steps=max_turns + 5,
    )
