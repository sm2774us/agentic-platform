"""Top-level orchestration: wires agents, RAG, tools, eval, and tracking."""

from __future__ import annotations

import time
from dataclasses import dataclass

from agentic_platform.agents.graph import build_research_writer_graph
from agentic_platform.agents.state import AgentState
from agentic_platform.config.settings import Settings, get_settings
from agentic_platform.eval.framework import EvaluationVerdict, evaluate_run
from agentic_platform.eval.mlflow_tracking import NullRunTracker, RunTracker
from agentic_platform.orchestration.llm_client import LLMClient, build_llm_client
from agentic_platform.rag.pipeline import HybridRetriever, chunk_document
from agentic_platform.tools.registry import ToolRegistry, default_tool_registry


@dataclass(slots=True, frozen=True)
class PipelineResult:
    state: AgentState
    verdict: EvaluationVerdict


class AgenticPipeline:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        llm: LLMClient | None = None,
        retriever: HybridRetriever | None = None,
        tools: ToolRegistry | None = None,
        tracker: RunTracker | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.llm = llm or build_llm_client(self.settings)
        self.retriever = retriever or HybridRetriever()
        self.tools = tools or default_tool_registry()
        self.tracker = tracker or NullRunTracker()
        self.graph = build_research_writer_graph(
            llm=self.llm,
            retriever=self.retriever,
            tools=self.tools,
            max_turns=self.settings.max_agent_turns,
        )

    def seed_knowledge_base(self, documents: dict[str, str]) -> None:
        for doc_id, text in documents.items():
            self.retriever.index(chunk_document(doc_id, text, source=doc_id))

    def run(self, task: str) -> PipelineResult:
        start = time.perf_counter()
        state = self.graph.run(AgentState(task=task))
        latency_ms = (time.perf_counter() - start) * 1000

        last_response_tokens = sum(len(m.content.split()) for m in state.messages)
        cost_usd = (last_response_tokens / 1000) * 0.01

        verdict = evaluate_run(
            state, settings=self.settings, latency_ms=latency_ms, cost_usd=cost_usd
        )
        self.tracker.log_run(task=task, verdict=verdict)
        return PipelineResult(state=state, verdict=verdict)
