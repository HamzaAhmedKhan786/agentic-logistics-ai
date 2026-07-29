from __future__ import annotations

import logging
from math import asin, cos, radians, sin, sqrt

import httpx

from config.settings import settings
from models.schemas import Coordinate, RouteLeg, Stop
from tools.polyline import decode_google_polyline, decode_here_polyline

logger = logging.getLogger(__name__)


def haversine_km(first: Stop, second: Stop) -> float:
    if None in (first.latitude, first.longitude, second.latitude, second.longitude):
        raise ValueError("Stops must be geocoded before routing")
    lat1, lon1, lat2, lon2 = map(
        radians,
        [first.latitude, first.longitude, second.latitude, second.longitude],
    )
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1
    value = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    return 6371 * 2 * asin(sqrt(value))


def nearest_neighbor(depot: Stop, stops: list[Stop]) -> list[Stop]:
    remaining = stops.copy()
    ordered: list[Stop] = []
    current = depot
    while remaining:
        next_stop = min(remaining, key=lambda candidate: haversine_km(current, candidate))
        ordered.append(next_stop)
        remaining.remove(next_stop)
        current = next_stop
    return ordered


def build_legs(depot: Stop, stops: list[Stop], average_speed_kph: float = 35) -> list[RouteLeg]:
    points = [depot, *stops, depot]
    legs: list[RouteLeg] = []
    for origin, destination in zip(points, points[1:]):
        distance = haversine_km(origin, destination)
        legs.append(
            RouteLeg(
                origin=origin.name,
                destination=destination.name,
                distance_km=round(distance, 2),
                duration_minutes=round(distance / average_speed_kph * 60, 1),
            )
        )
    return legs


def route_coordinates(depot: Stop, stops: list[Stop]) -> list[Coordinate]:
    return [
        Coordinate(latitude=point.latitude, longitude=point.longitude)
        for point in [depot, *stops, depot]
        if point.latitude is not None and point.longitude is not None
    ]


async def _here_legs(depot: Stop, stops: list[Stop]) -> tuple[list[RouteLeg], list[Coordinate]]:
    params: list[tuple[str, str]] = [
        ("transportMode", "car"),
        ("origin", f"{depot.latitude},{depot.longitude}"),
        ("destination", f"{depot.latitude},{depot.longitude}"),
        ("return", "summary,polyline"),
        ("apiKey", settings.here_api_key or ""),
    ]
    params.extend(
        ("via", f"{stop.latitude},{stop.longitude}") for stop in stops
    )
    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        response = await client.get("https://router.hereapi.com/v8/routes", params=params)
        response.raise_for_status()
        routes = response.json().get("routes", [])
    if not routes:
        raise ValueError("HERE could not construct the requested route")
    sections = routes[0]["sections"]
    points = [depot, *stops, depot]
    legs = [
        RouteLeg(
            origin=origin.name,
            destination=destination.name,
            distance_km=round(section["summary"]["length"] / 1000, 2),
            duration_minutes=round(section["summary"]["duration"] / 60, 1),
        )
        for section, (origin, destination) in zip(sections, zip(points, points[1:]))
    ]
    geometry = [
        coordinate
        for section in sections
        for coordinate in decode_here_polyline(section["polyline"])
    ]
    return legs, geometry


async def _google_legs(depot: Stop, stops: list[Stop]) -> tuple[list[RouteLeg], list[Coordinate]]:
    waypoint = lambda point: {
        "location": {
            "latLng": {"latitude": point.latitude, "longitude": point.longitude}
        }
    }
    body = {
        "origin": waypoint(depot),
        "destination": waypoint(depot),
        "intermediates": [waypoint(stop) for stop in stops],
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE",
    }
    headers = {
        "X-Goog-Api-Key": settings.google_maps_api_key or "",
        "X-Goog-FieldMask": (
            "routes.legs.distanceMeters,routes.legs.duration,"
            "routes.polyline.encodedPolyline"
        ),
    }
    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        response = await client.post(
            "https://routes.googleapis.com/directions/v2:computeRoutes",
            json=body,
            headers=headers,
        )
        response.raise_for_status()
        routes = response.json().get("routes", [])
    if not routes:
        raise ValueError("Google could not construct the requested route")
    points = [depot, *stops, depot]
    legs = [
        RouteLeg(
            origin=origin.name,
            destination=destination.name,
            distance_km=round(leg["distanceMeters"] / 1000, 2),
            duration_minutes=round(float(leg["duration"].removesuffix("s")) / 60, 1),
        )
        for leg, (origin, destination) in zip(
            routes[0]["legs"], zip(points, points[1:])
        )
    ]
    geometry = decode_google_polyline(routes[0]["polyline"]["encodedPolyline"])
    return legs, geometry


async def _osrm_legs(
    depot: Stop, stops: list[Stop]
) -> tuple[list[RouteLeg], list[Coordinate]]:
    points = [depot, *stops, depot]
    coordinates = ";".join(
        f"{point.longitude},{point.latitude}" for point in points
    )
    url = (
        f"{settings.osrm_base_url.rstrip('/')}/route/v1/driving/{coordinates}"
    )
    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        response = await client.get(
            url,
            params={
                "overview": "full",
                "geometries": "geojson",
                "steps": "false",
            },
            headers={"User-Agent": "RouteMind-Agentic-Logistics/0.1"},
        )
        response.raise_for_status()
        payload = response.json()
    if payload.get("code") != "Ok" or not payload.get("routes"):
        raise ValueError(f"OSRM routing failed: {payload.get('message', 'unknown')}")
    route = payload["routes"][0]
    legs = [
        RouteLeg(
            origin=origin.name,
            destination=destination.name,
            distance_km=round(leg["distance"] / 1000, 2),
            duration_minutes=round(leg["duration"] / 60, 1),
        )
        for leg, (origin, destination) in zip(
            route["legs"], zip(points, points[1:])
        )
    ]
    geometry = [
        Coordinate(latitude=latitude, longitude=longitude)
        for longitude, latitude in route["geometry"]["coordinates"]
    ]
    return legs, geometry


async def build_provider_legs(
    depot: Stop, stops: list[Stop]
) -> tuple[list[RouteLeg], str, list[Coordinate]]:
    provider = settings.routing_provider.lower()
    if provider == "here":
        legs, geometry = await _here_legs(depot, stops)
        return legs, "here", geometry
    if provider == "google":
        legs, geometry = await _google_legs(depot, stops)
        return legs, "google", geometry
    if provider == "osrm":
        try:
            legs, geometry = await _osrm_legs(depot, stops)
            return legs, "osrm", geometry
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            logger.warning("OSRM unavailable; using simulated route geometry: %s", exc)
            return (
                build_legs(depot, stops),
                "simulated-fallback",
                route_coordinates(depot, stops),
            )
    return build_legs(depot, stops), "simulated", route_coordinates(depot, stops)
