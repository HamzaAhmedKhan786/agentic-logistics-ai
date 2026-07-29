import asyncio

from agents import disruption_agent
from config.llm import llm
from config.settings import settings
from models.schemas import PlanRequest, RouteLeg, Stop, Vehicle, VehicleRoute
from models.state import LogisticsState


def test_live_disruption_is_matched_to_route(monkeypatch) -> None:
    source_url = "https://www.berlin.de/example-closure"

    async def fake_search():
        return [
            {
                "title": "Closure on Friedrichstrasse",
                "url": source_url,
                "content": "Friedrichstrasse is closed today.",
                "published_date": "2026-07-30",
                "score": 0.98,
            }
        ]

    async def fake_extract(system_prompt, user_payload, fallback):
        return {
            "disruptions": [
                {
                    "title": "Closure on Friedrichstrasse",
                    "summary": "The road is closed today.",
                    "affected_locations": ["Friedrichstrasse"],
                    "disruption_type": "closure",
                    "status": "active",
                    "confidence": 0.95,
                    "source_url": source_url,
                    "published_at": "2026-07-30",
                }
            ]
        }

    monkeypatch.setattr(disruption_agent, "search_berlin_disruptions", fake_search)
    monkeypatch.setattr(llm, "complete_json", fake_extract)
    monkeypatch.setattr(settings, "tavily_api_key", "test-key")

    depot = Stop(name="Hub", address="Alexanderplatz")
    destination = Stop(
        name="Mitte office", address="Friedrichstrasse, Berlin", demand_kg=10
    )
    state = LogisticsState(
        request=PlanRequest(
            depot=depot,
            stops=[destination],
            vehicles=[Vehicle(id="VAN-01", capacity_kg=100)],
            simulate_traffic=False,
        ),
        routes=[
            VehicleRoute(
                vehicle_id="VAN-01",
                stops=[destination],
                legs=[
                    RouteLeg(
                        origin="Alexanderplatz",
                        destination="Friedrichstrasse, Berlin",
                        distance_km=3,
                        duration_minutes=10,
                    )
                ],
                total_distance_km=3,
                total_duration_minutes=10,
                total_load_kg=10,
                estimated_cost=3,
            )
        ],
    )

    asyncio.run(disruption_agent.run(state))

    assert state.disruptions[0].affected_vehicle_ids == ["VAN-01"]
    assert state.issues[0].code == "LIVE_ROAD_DISRUPTION"
    assert state.issues[0].severity == "error"
