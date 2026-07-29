from __future__ import annotations

import hashlib
import random

from models.schemas import ValidationIssue
from models.state import LogisticsState
from tools.traffic_provider import observe_traffic


LEVELS = [
    ("clear", 1.0),
    ("light", 1.12),
    ("moderate", 1.3),
    ("heavy", 1.65),
]


async def run(state: LogisticsState) -> LogisticsState:
    """Apply reproducible synthetic traffic for demos and resilience testing."""
    if not state.request.simulate_traffic:
        return state

    heavy_routes: list[str] = []
    for route in state.routes:
        seed_material = (
            f"{state.request.traffic_seed}|{state.replans}|{route.vehicle_id}|"
            f"{','.join(stop.address for stop in route.stops)}"
        )
        seed = int(hashlib.sha256(seed_material.encode()).hexdigest()[:16], 16)
        observation = await observe_traffic(route)
        if observation:
            level, factor = observation.level, observation.factor
        else:
            level, factor = random.Random(seed).choices(
                LEVELS, weights=[40, 30, 22, 8], k=1
            )[0]
        original = route.total_duration_minutes
        route.traffic_level = level
        route.traffic_delay_minutes = round(original * (factor - 1), 1)
        route.total_duration_minutes = round(original * factor, 1)
        if level == "heavy":
            heavy_routes.append(route.vehicle_id)

    state.issues = [
        issue for issue in state.issues if issue.code != "TRAFFIC_CHANGED"
    ] + ([
        ValidationIssue(
            code="TRAFFIC_CHANGED",
            message=f"Heavy simulated congestion affects: {', '.join(heavy_routes)}",
            severity="error",
        )
    ] if heavy_routes else [])
    state.emit(
        "traffic",
        "sample_conditions",
        (
            f"Heavy congestion detected on {len(heavy_routes)} route(s)"
            if heavy_routes
            else "Synthetic traffic sampled; no critical congestion detected"
        ),
    )
    return state
