from config.llm import llm
from config.metrics import REPLANS
from models.state import LogisticsState


async def run(state: LogisticsState) -> LogisticsState:
    issue_codes = [issue.code for issue in state.issues]
    fallback = {
        "action": "prioritize_high_capacity_vehicles",
        "reasoning": "Capacity-first retry is the safest deterministic adjustment.",
    }
    decision = await llm.complete_json(
        """You are a logistics replanning agent. Given validation issue codes,
choose one safe recovery action. Return JSON with action and reasoning. Supported
actions are prioritize_high_capacity_vehicles and retry_route_order. Never relax
hard safety constraints.""",
        {
            "issues": issue_codes,
            "previous_strategy": state.plan_strategy,
            "attempt": state.replans + 1,
        },
        fallback,
    )
    if "TRAFFIC_CHANGED" in issue_codes:
        state.traffic_reroute = True
    if "LIVE_ROAD_DISRUPTION" in issue_codes:
        state.traffic_reroute = True
    if "SEVERE_WEATHER" in issue_codes:
        state.traffic_reroute = True
    state.request.vehicles.sort(key=lambda vehicle: vehicle.capacity_kg, reverse=True)
    state.replans += 1
    REPLANS.labels(reason=",".join(issue_codes) or "unknown").inc()
    state.emit(
        "replanner",
        "adjust_strategy",
        f"Retry {state.replans}: {decision.get('reasoning', fallback['reasoning'])}",
    )
    return state
