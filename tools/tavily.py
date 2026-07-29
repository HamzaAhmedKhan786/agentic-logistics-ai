from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


async def search_berlin_disruptions() -> list[dict[str, Any]]:
    """Search recent Berlin transport disruption reports.

    Search results are intelligence signals, not authoritative routing rules.
    """
    if not settings.tavily_enabled or not settings.tavily_api_key:
        return []

    today = datetime.now(timezone.utc).date().isoformat()
    payload = {
        "query": (
            f"Berlin breaking news Eilmeldung Unwetter Streik Lieferkette "
            f"Logistikstörung Straßensperrung Baustelle Demonstration Unfall "
            f"Umleitung LKW Verkehrsbehinderung Flughafen Bahn Lager {today}"
        ),
        "topic": "news",
        "time_range": "week",
        "search_depth": settings.tavily_search_depth,
        "max_results": settings.tavily_max_results,
        "include_answer": False,
        "include_raw_content": False,
        "include_domains": [
            "berlin.de",
            "viz.berlin.de",
            "rbb24.de",
            "tagesspiegel.de",
            "morgenpost.de",
            "dwd.de",
            "polizei.berlin",
            "verkehrsmeldungen.de",
        ],
    }
    headers = {
        "Authorization": f"Bearer {settings.tavily_api_key}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(
            timeout=settings.request_timeout_seconds
        ) as client:
            response = await client.post(
                TAVILY_SEARCH_URL, headers=headers, json=payload
            )
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Tavily disruption search failed: %s", exc)
        return []
