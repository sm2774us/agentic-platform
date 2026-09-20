"""Centralized, environment-driven application settings."""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    LOCAL = "local"
    STAGING = "staging"
    PRODUCTION = "production"


class LLMProvider(StrEnum):
    MOCK = "mock"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AGENTIC_", env_file=".env", extra="ignore")

    environment: Environment = Environment.LOCAL
    llm_provider: LLMProvider = LLMProvider.MOCK
    llm_model_name: str = "mock-model-large"
    max_agent_turns: int = Field(default=8, ge=1, le=50)
    request_timeout_seconds: float = Field(default=30.0, gt=0)
    max_retries: int = Field(default=3, ge=0, le=10)
    retrieval_top_k: int = Field(default=5, ge=1, le=50)
    hallucination_score_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    cost_budget_usd_per_request: float = Field(default=0.50, gt=0)
    mlflow_tracking_uri: str = "file:./mlruns"
    otel_service_name: str = "agentic-platform"
    enable_human_in_the_loop: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
