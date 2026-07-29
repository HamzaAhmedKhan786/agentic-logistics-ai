from __future__ import annotations

import logging

import httpx

from config.settings import settings
from models.schemas import WeatherSnapshot

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

CONDITIONS = {
    0: "Clear",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Freezing fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Heavy drizzle",
    56: "Freezing drizzle",
    57: "Heavy freezing drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    66: "Freezing rain",
    67: "Heavy freezing rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Light showers",
    81: "Showers",
    82: "Heavy showers",
    85: "Snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Severe thunderstorm with hail",
}

SEVERE_WEATHER_CODES = {65, 67, 75, 77, 82, 85, 86, 95, 96, 99}


async def current_berlin_weather() -> WeatherSnapshot | None:
    if not settings.weather_enabled:
        return None
    params = {
        "latitude": settings.weather_latitude,
        "longitude": settings.weather_longitude,
        "current": (
            "temperature_2m,apparent_temperature,precipitation,snowfall,"
            "weather_code,wind_speed_10m,wind_gusts_10m,visibility"
        ),
        "timezone": "Europe/Berlin",
    }
    try:
        async with httpx.AsyncClient(
            timeout=settings.request_timeout_seconds
        ) as client:
            response = await client.get(OPEN_METEO_URL, params=params)
            response.raise_for_status()
            current = response.json()["current"]
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        logger.warning("Current weather lookup failed: %s", exc)
        return None

    code = int(current["weather_code"])
    gust = float(current["wind_gusts_10m"])
    visibility = current.get("visibility")
    severe = (
        code in SEVERE_WEATHER_CODES
        or gust >= settings.severe_wind_gust_kmh
        or (visibility is not None and float(visibility) < 500)
    )
    return WeatherSnapshot(
        observed_at=str(current["time"]),
        temperature_c=float(current["temperature_2m"]),
        apparent_temperature_c=float(current["apparent_temperature"]),
        precipitation_mm=float(current["precipitation"]),
        snowfall_cm=float(current["snowfall"]),
        wind_speed_kmh=float(current["wind_speed_10m"]),
        wind_gust_kmh=gust,
        visibility_m=float(visibility) if visibility is not None else None,
        weather_code=code,
        condition=CONDITIONS.get(code, f"WMO weather code {code}"),
        severe=severe,
    )
