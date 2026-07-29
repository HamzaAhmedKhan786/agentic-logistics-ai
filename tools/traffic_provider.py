from __future__ import annotations

from dataclasses import dataclass

import httpx

from config.settings import settings
from models.schemas import VehicleRoute


@dataclass
class TrafficObservation:
    level: str
    factor: float
    provider: str


def _level(factor: float) -> str:
    if factor >= 1.5:
        return "heavy"
    if factor >= 1.25:
        return "moderate"
    if factor >= 1.08:
        return "light"
    return "clear"


async def observe_here(route: VehicleRoute) -> TrafficObservation:
    points = route.route_coordinates
    params: list[tuple[str, str]] = [
        ("transportMode", "car"),
        ("origin", f"{points[0].latitude},{points[0].longitude}"),
        ("destination", f"{points[-1].latitude},{points[-1].longitude}"),
        ("return", "summary"),
        ("apiKey", settings.here_api_key or ""),
    ]
    params.extend(
        ("via", f"{stop.latitude},{stop.longitude}")
        for stop in route.stops
        if stop.latitude is not None and stop.longitude is not None
    )
    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        response = await client.get("https://router.hereapi.com/v8/routes", params=params)
        response.raise_for_status()
        sections = response.json()["routes"][0]["sections"]
    duration = sum(section["summary"]["duration"] for section in sections)
    base = sum(
        section["summary"].get("baseDuration", section["summary"]["duration"])
        for section in sections
    )
    factor = duration / max(base, 1)
    return TrafficObservation(_level(factor), factor, "here")


async def observe_google(route: VehicleRoute) -> TrafficObservation:
    points = route.route_coordinates
    waypoint = lambda point: {
        "location": {
            "latLng": {"latitude": point.latitude, "longitude": point.longitude}
        }
    }
    body = {
        "origin": waypoint(points[0]),
        "destination": waypoint(points[-1]),
        "intermediates": [
            waypoint(stop)
            for stop in route.stops
            if stop.latitude is not None and stop.longitude is not None
        ],
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE_OPTIMAL",
    }
    headers = {
        "X-Goog-Api-Key": settings.google_maps_api_key or "",
        "X-Goog-FieldMask": "routes.duration,routes.staticDuration",
    }
    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        response = await client.post(
            "https://routes.googleapis.com/directions/v2:computeRoutes",
            json=body,
            headers=headers,
        )
        response.raise_for_status()
        result = response.json()["routes"][0]
    seconds = lambda value: float(value.removesuffix("s"))
    factor = seconds(result["duration"]) / max(seconds(result["staticDuration"]), 1)
    return TrafficObservation(_level(factor), factor, "google")


async def observe_traffic(route: VehicleRoute) -> TrafficObservation | None:
    provider = settings.traffic_provider.lower()
    if provider == "here" and settings.here_api_key:
        return await observe_here(route)
    if provider == "google" and settings.google_maps_api_key:
        return await observe_google(route)
    return None
