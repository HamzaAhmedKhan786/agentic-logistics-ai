from models.state import LogisticsState


async def run(state: LogisticsState) -> LogisticsState:
    distance = sum(route.total_distance_km for route in state.routes)
    cost = sum(route.estimated_cost for route in state.routes)
    hard_errors = [issue for issue in state.issues if issue.severity == "error"]
    state.status = "completed" if not hard_errors and not state.unassigned_stops else "partial"
    state.summary = (
        f"{len(state.routes)} route(s), {distance:.1f} km total, estimated cost "
        f"{cost:.2f}; {len(state.unassigned_stops)} unassigned stop(s)."
    )
    state.emit("finalizer", "produce_answer", state.summary)
    return state
