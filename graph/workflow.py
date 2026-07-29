from agents import (
    executor_agent,
    disruption_agent,
    finalizer_agent,
    planner_agent,
    reflection_agent,
    replanner_agent,
    traffic_agent,
    weather_agent,
)
from graph.checkpoints import save_checkpoint
from graph.routing import should_replan
from graph.comparison import compare_plans
from config.settings import settings
from models.schemas import PlanRequest, PlanResponse
from models.state import LogisticsState


async def run_workflow(request: PlanRequest) -> PlanResponse:
    state = LogisticsState(request=request)
    await planner_agent.run(state)

    while True:
        await executor_agent.run(state)
        await weather_agent.run(state)
        await disruption_agent.run(state)
        await traffic_agent.run(state)
        await reflection_agent.run(state)
        if not should_replan(state):
            break
        if not state.baseline_routes:
            state.baseline_routes = [
                route.model_copy(deep=True) for route in state.routes
            ]
        await replanner_agent.run(state)

    await finalizer_agent.run(state)
    state.comparison = compare_plans(state.baseline_routes, state.routes)
    live_disruption_review = any(
        issue.code in {"LIVE_ROAD_DISRUPTION", "SEVERE_WEATHER"}
        for issue in state.issues
    )
    approval_required = bool(
        (state.replans and state.comparison.get("changed"))
        or live_disruption_review
    )
    if approval_required:
        state.status = "awaiting_approval"
    response = PlanResponse(
        status=state.status,
        objective=request.objective,
        routes=state.routes,
        unassigned_stops=state.unassigned_stops,
        issues=state.issues,
        disruptions=state.disruptions,
        weather=state.weather,
        events=state.events,
        replans=state.replans,
        summary=state.summary,
        location_provider=settings.location_provider,
        comparison=state.comparison,
        approval_required=approval_required,
    )
    save_checkpoint(response)
    return response
