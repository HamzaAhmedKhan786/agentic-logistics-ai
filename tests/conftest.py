import pytest

from config.llm import llm
from config.settings import settings


@pytest.fixture(autouse=True)
def isolate_external_providers(monkeypatch):
    """Unit tests never consume LLM quota or call external map services."""
    monkeypatch.setattr(llm, "provider", "mock")
    monkeypatch.setattr(settings, "location_provider", "simulated")
    monkeypatch.setattr(settings, "routing_provider", "simulated")
    monkeypatch.setattr(settings, "traffic_provider", "synthetic")
    monkeypatch.setattr(settings, "tavily_api_key", None)
    monkeypatch.setattr(settings, "weather_enabled", False)
