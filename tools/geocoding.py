from __future__ import annotations

import hashlib

import httpx

from config.settings import settings
from models.schemas import Stop


def geocode(stop: Stop) -> Stop:
    """Provide stable demo coordinates when coordinates were not supplied."""
    if stop.latitude is not None and stop.longitude is not None:
        return stop
    digest = hashlib.sha256(stop.address.encode("utf-8")).digest()
    # Stable coordinates around Berlin; replace with a production geocoder adapter.
    lat = 52.35 + int.from_bytes(digest[:2], "big") / 65535 * 0.35
    lon = 13.15 + int.from_bytes(digest[2:4], "big") / 65535 * 0.45
    return stop.model_copy(update={"latitude": round(lat, 6), "longitude": round(lon, 6)})


def geocode_many(stops: list[Stop]) -> list[Stop]:
    return [geocode(stop) for stop in stops]


async def _geocode_here(stop: Stop) -> Stop:
    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        response = await client.get(
            "https://geocode.search.hereapi.com/v1/geocode",
            params={"q": stop.address, "apiKey": settings.here_api_key, "limit": 1},
        )
        response.raise_for_status()
        items = response.json().get("items", [])
    if not items:
        raise ValueError(f"HERE could not geocode: {stop.address}")
    position = items[0]["position"]
    return stop.model_copy(
        update={"latitude": position["lat"], "longitude": position["lng"]}
    )


async def _geocode_google(stop: Stop) -> Stop:
    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        response = await client.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={"address": stop.address, "key": settings.google_maps_api_key},
        )
        response.raise_for_status()
        payload = response.json()
    if payload.get("status") != "OK" or not payload.get("results"):
        raise ValueError(
            f"Google could not geocode {stop.address}: {payload.get('status', 'UNKNOWN')}"
        )
    location = payload["results"][0]["geometry"]["location"]
    return stop.model_copy(
        update={"latitude": location["lat"], "longitude": location["lng"]}
    )


async def geocode_real(stop: Stop) -> Stop:
    """Geocode with the configured provider; coordinates supplied by users win."""
    if stop.latitude is not None and stop.longitude is not None:
        return stop
    provider = settings.location_provider.lower()
    if provider == "here":
        if not settings.here_api_key:
            raise ValueError("HERE_API_KEY is required when LOCATION_PROVIDER=here")
        return await _geocode_here(stop)
    if provider == "google":
        if not settings.google_maps_api_key:
            raise ValueError(
                "GOOGLE_MAPS_API_KEY is required when LOCATION_PROVIDER=google"
            )
        return await _geocode_google(stop)
    return geocode(stop)


async def geocode_many_real(stops: list[Stop]) -> list[Stop]:
    # Sequential calls avoid surprising provider bursts and simplify rate control.
    return [await geocode_real(stop) for stop in stops]
