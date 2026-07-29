import asyncio

from agents import weather_agent
from models.schemas import PlanRequest, Stop, Vehicle, WeatherSnapshot
from models.state import LogisticsState


def test_severe_current_weather_requires_review(monkeypatch) -> None:
    async def fake_weather():
        return WeatherSnapshot(
            observed_at="2026-07-30T12:00",
            temperature_c=22,
            apparent_temperature_c=21,
            precipitation_mm=4,
            snowfall_cm=0,
            wind_speed_kmh=48,
            wind_gust_kmh=82,
            visibility_m=3000,
            weather_code=95,
            condition="Thunderstorm",
            severe=True,
        )

    monkeypatch.setattr(weather_agent, "current_berlin_weather", fake_weather)
    state = LogisticsState(
        request=PlanRequest(
            depot=Stop(name="Hub", address="Alexanderplatz"),
            stops=[Stop(name="A", address="Mitte", demand_kg=10)],
            vehicles=[Vehicle(id="VAN-01", capacity_kg=100)],
        )
    )

    asyncio.run(weather_agent.run(state))

    assert state.weather is not None
    assert state.weather.severe is True
    assert state.issues[0].code == "SEVERE_WEATHER"
