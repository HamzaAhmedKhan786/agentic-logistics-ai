from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    app_name: str = "Agentic Logistics AI"
    app_env: str = "development"
    llm_provider: str = "mock"
    llm_model: str = "gpt-4.1-mini"
    groq_api_key: str | None = None
    openai_api_key: str | None = None
    location_provider: str = "simulated"
    routing_provider: str = "osrm"
    osrm_base_url: str = "https://router.project-osrm.org"
    here_api_key: str | None = None
    google_maps_api_key: str | None = None
    tavily_api_key: str | None = None
    tavily_enabled: bool = True
    tavily_search_depth: str = "basic"
    tavily_max_results: int = 8
    disruption_confidence_threshold: float = 0.75
    weather_enabled: bool = True
    weather_latitude: float = 52.52
    weather_longitude: float = 13.405
    severe_wind_gust_kmh: float = 70
    use_ortools: bool = True
    database_url: str = "sqlite+aiosqlite:///./output/logistics.db"
    traffic_provider: str = "synthetic"
    traffic_poll_seconds: int = 60
    log_level: str = "INFO"
    prometheus_pushgateway: str = "http://localhost:9091"
    run_llm_evals: bool = False
    max_replans: int = 2
    request_timeout_seconds: float = 20

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
