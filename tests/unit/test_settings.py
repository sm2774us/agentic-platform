from agentic_platform.config.settings import Environment, LLMProvider, Settings, get_settings


def test_default_settings_values() -> None:
    settings = Settings()
    assert settings.environment == Environment.LOCAL
    assert settings.llm_provider == LLMProvider.MOCK
    assert settings.max_agent_turns == 8


def test_get_settings_is_cached() -> None:
    assert get_settings() is get_settings()


def test_settings_bounds_enforced() -> None:
    settings = Settings(max_agent_turns=1, hallucination_score_threshold=0.0)
    assert settings.max_agent_turns == 1
    assert settings.hallucination_score_threshold == 0.0
