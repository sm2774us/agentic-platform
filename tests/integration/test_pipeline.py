from agentic_platform.config.settings import Settings
from agentic_platform.eval.mlflow_tracking import NullRunTracker
from agentic_platform.orchestration.llm_client import MockLLMClient
from agentic_platform.orchestration.pipeline import AgenticPipeline


def test_pipeline_end_to_end_run() -> None:
    settings = Settings(max_agent_turns=3)
    llm = MockLLMClient(settings, canned_responses={"onboarding": "Read the runbooks first."})
    tracker = NullRunTracker()
    pipeline = AgenticPipeline(settings=settings, llm=llm, tracker=tracker)
    pipeline.seed_knowledge_base({"doc1": "Onboarding requires reading the runbooks."})

    result = pipeline.run("onboarding steps")

    assert result.state.final_answer
    assert result.verdict.scores.latency_ms >= 0
    assert len(tracker.calls) == 1


def test_pipeline_uses_default_settings_when_unspecified() -> None:
    pipeline = AgenticPipeline()
    assert pipeline.settings.llm_provider.value == "mock"
    result = pipeline.run("a task with no seeded knowledge")
    assert result.state.final_answer is not None
