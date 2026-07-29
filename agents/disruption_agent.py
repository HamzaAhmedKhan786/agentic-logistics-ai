from __future__ import annotations

import re
from typing import Any

from config.llm import llm
from config.settings import settings
from models.schemas import DisruptionSignal, ValidationIssue
from models.state import LogisticsState
from tools.tavily import search_berlin_disruptions


def _route_text(route: Any) -> str:
    values = [route.vehicle_id]
    values.extend(f"{stop.name} {stop.address}" for stop in route.stops)
    values.extend(f"{leg.origin} {leg.destination}" for leg in route.legs)
    return " ".join(values).casefold()


def _location_matches_route(location: str, route: Any) -> bool:
    location_text = location.casefold().strip()
    if len(location_text) < 4:
        return False
    route_text = _route_text(route)
    if location_text in route_text:
        return True
    tokens = {
        token
        for token in re.findall(r"[\wäöüß-]{5,}", location_text)
        if token not in {"berlin", "straße", "strasse"}
    }
    return bool(tokens and any(token in route_text for token in tokens))


async def run(state: LogisticsState) -> LogisticsState:
    if state.disruptions_checked:
        return state
    state.disruptions_checked = True

    results = await search_berlin_disruptions()
    if not results:
        if settings.tavily_enabled and settings.tavily_api_key:
            state.emit(
                "disruption_research",
                "search_live_reports",
                "No usable recent Berlin disruption reports were returned",
            )
        return state

    compact_results = [
        {
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "content": item.get("content", ""),
            "published_date": item.get("published_date"),
            "score": item.get("score"),
        }
        for item in results
    ]
    extraction = await llm.complete_json(
        """You extract current Berlin road disruptions from supplied web search
results. Return JSON with a `disruptions` array. Each item must contain title,
summary, affected_locations (specific roads, intersections, districts or places),
disruption_type (closure, construction, demonstration, accident, severe_weather,
strike, supply_chain, airport, rail, warehouse, or other), status (active,
planned, expired, or unverified), confidence from 0 to 1,
source_url, and published_at. Do not invent locations, dates, status, or URLs.
Only label a disruption active when the source clearly supports that it is active
now. Omit general traffic articles and items unrelated to road logistics.""",
        {"search_results": compact_results},
        {"disruptions": []},
    )

    valid_urls = {str(item.get("url", "")) for item in compact_results}
    signals: list[DisruptionSignal] = []
    for item in extraction.get("disruptions", []):
        if not isinstance(item, dict) or item.get("source_url") not in valid_urls:
            continue
        try:
            signal = DisruptionSignal.model_validate(item)
        except ValueError:
            continue
        signal.affected_vehicle_ids = [
            route.vehicle_id
            for route in state.routes
            if any(
                _location_matches_route(location, route)
                for location in signal.affected_locations
            )
        ]
        signals.append(signal)

    state.disruptions = signals
    actionable = [
        signal
        for signal in signals
        if signal.status == "active"
        and signal.confidence >= settings.disruption_confidence_threshold
        and signal.affected_vehicle_ids
    ]
    for signal in actionable:
        state.issues.append(
            ValidationIssue(
                code="LIVE_ROAD_DISRUPTION",
                message=(
                    f"{signal.title} may affect "
                    f"{', '.join(signal.affected_vehicle_ids)}. "
                    f"Dispatcher verification required: {signal.source_url}"
                ),
                severity="error",
            )
        )
    state.emit(
        "disruption_research",
        "search_live_reports",
        (
            f"Structured {len(signals)} disruption signal(s); "
            f"{len(actionable)} matched active route(s)"
        ),
    )
    return state
