from __future__ import annotations

from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from agents import (
    disruption_agent,
    executor_agent,
    finalizer_agent,
    planner_agent,
    reflection_agent,
    replanner_agent,
    traffic_agent,
    weather_agent,
)
from config.settings import settings
from graph.checkpoints import save_checkpoint
from graph.comparison import compare_plans
from graph.routing import should_replan
from models.schemas import PlanRequest, PlanResponse
from models.state import LogisticsState


class WorkflowState(TypedDict):
    """LangGraph channel containing the typed logistics domain state."""

    logistics: LogisticsState


async def planner_node(graph_state: WorkflowState) -> dict:
    state = await planner_agent.run(graph_state["logistics"])
    return {"logistics": state}


async def executor_node(graph_state: WorkflowState) -> dict:
    state = await executor_agent.run(graph_state["logistics"])
    return {"logistics": state}


async def weather_node(graph_state: WorkflowState) -> dict:
    state = await weather_agent.run(graph_state["logistics"])
    return {"logistics": state}


async def disruption_node(graph_state: WorkflowState) -> dict:
    state = await disruption_agent.run(graph_state["logistics"])
    return {"logistics": state}


async def traffic_node(graph_state: WorkflowState) -> dict:
    state = await traffic_agent.run(graph_state["logistics"])
    return {"logistics": state}


async def reflection_node(graph_state: WorkflowState) -> dict:
    state = await reflection_agent.run(graph_state["logistics"])
    return {"logistics": state}


async def replanner_node(graph_state: WorkflowState) -> dict:
    state = graph_state["logistics"]
    if not state.baseline_routes:
        state.baseline_routes = [
            route.model_copy(deep=True) for route in state.routes
        ]
    state = await replanner_agent.run(state)
    return {"logistics": state}


async def finalizer_node(graph_state: WorkflowState) -> dict:
    state = await finalizer_agent.run(graph_state["logistics"])
    return {"logistics": state}


def route_after_reflection(
    graph_state: WorkflowState,
) -> Literal["replanner", "finalizer"]:
    return (
        "replanner"
        if should_replan(graph_state["logistics"])
        else "finalizer"
    )


def build_workflow() -> StateGraph:
    builder = StateGraph(WorkflowState)
    builder.add_node("planner", planner_node)
    builder.add_node("executor", executor_node)
    builder.add_node("weather", weather_node)
    builder.add_node("disruption_research", disruption_node)
    builder.add_node("traffic", traffic_node)
    builder.add_node("reflection", reflection_node)
    builder.add_node("replanner", replanner_node)
    builder.add_node("finalizer", finalizer_node)

    builder.add_edge(START, "planner")
    builder.add_edge("planner", "executor")
    builder.add_edge("executor", "weather")
    builder.add_edge("weather", "disruption_research")
    builder.add_edge("disruption_research", "traffic")
    builder.add_edge("traffic", "reflection")
    builder.add_conditional_edges(
        "reflection",
        route_after_reflection,
        {"replanner": "replanner", "finalizer": "finalizer"},
    )
    builder.add_edge("replanner", "executor")
    builder.add_edge("finalizer", END)
    return builder


workflow_builder = build_workflow()
workflow_graph = workflow_builder.compile()


async def run_workflow(request: PlanRequest) -> PlanResponse:
    result = await workflow_graph.ainvoke(
        {"logistics": LogisticsState(request=request)},
        config={"recursion_limit": max(25, settings.max_replans * 8 + 10)},
    )
    state = result["logistics"]
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
