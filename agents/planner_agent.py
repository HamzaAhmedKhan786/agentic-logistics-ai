from config.llm import llm
from models.state import LogisticsState
from tools.rag import retrieve_policies


async def run(state: LogisticsState) -> LogisticsState:
    policies = retrieve_policies(state.request.objective)
    fallback = {
        "strategy": "capacity-first assignment followed by nearest-neighbor routing",
        "constraints": policies,
        "vehicle_priority": "largest_remaining_capacity",
        "risk_flags": [],
        "reasoning": "This deterministic strategy satisfies hard capacity checks first.",
    }
    decision = await llm.complete_json(
        """You are the planning node in a logistics agent system.
Return one JSON object with exactly these fields:
strategy (string), constraints (array of strings), vehicle_priority (string),
risk_flags (array of strings), reasoning (string).
Never invent distances or coordinates. Treat capacity and vehicle distance as
hard constraints. Keep reasoning concise and operational.""",
        state.request.model_dump(mode="json"),
        fallback,
    )
    state.plan_strategy = {**fallback, **decision}
    state.emit("planner", "create_strategy", decision.get("strategy", fallback["strategy"]))
    return state
