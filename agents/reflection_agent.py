from config.llm import llm
from models.schemas import ValidationIssue
from models.state import LogisticsState
from validators.route_validator import validate_route


async def run(state: LogisticsState) -> LogisticsState:
    vehicle_by_id = {vehicle.id: vehicle for vehicle in state.request.vehicles}
    issues = list(state.issues) + [
        issue
        for route in state.routes
        for issue in validate_route(route, vehicle_by_id[route.vehicle_id])
    ]
    if state.unassigned_stops:
        issues.append(
            ValidationIssue(
                code="UNASSIGNED_STOPS",
                message=f"{len(state.unassigned_stops)} stops could not fit available capacity",
                severity="warning",
            )
        )
    state.issues = issues
    fallback = {
        "verdict": "accept" if not issues else "revise",
        "recoverable": any(issue.severity == "error" for issue in issues),
        "recommended_action": (
            "finalize the feasible plan"
            if not issues
            else "address the reported deterministic validation issues"
        ),
        "explanation": "Deterministic validators remain the source of truth.",
    }
    llm_reflection = await llm.complete_json(
        """You are a logistics reflection agent. Review tool-computed routes and
validator issues. Return JSON fields verdict, recoverable, recommended_action,
and explanation. Never override or dismiss deterministic safety errors.""",
        {
            "strategy": state.plan_strategy,
            "routes": [route.model_dump(mode="json") for route in state.routes],
            "issues": [issue.model_dump(mode="json") for issue in issues],
        },
        fallback,
    )
    # The LLM may phrase a verdict differently (for example, "no_issues").
    # Keep its wording for auditability, but deterministic validation owns the
    # canonical workflow decision.
    state.reflection = {
        **fallback,
        **llm_reflection,
        "llm_verdict": llm_reflection.get("verdict"),
        "verdict": fallback["verdict"],
        "recoverable": fallback["recoverable"],
    }
    state.emit(
        "reflection",
        "validate_plan",
        state.reflection.get(
            "explanation",
            "Plan passed validation" if not issues else f"Found {len(issues)} issue(s)",
        ),
    )
    return state
