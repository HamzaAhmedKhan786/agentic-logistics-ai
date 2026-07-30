import asyncio

from config.settings import settings
from graph.workflow import (
    WorkflowState,
    route_after_reflection,
    run_workflow,
    workflow_graph,
)
from models.schemas import PlanRequest, Stop, ValidationIssue, Vehicle
from models.state import LogisticsState


def test_workflow_builds_auditable_plan() -> None:
    request = PlanRequest(
        depot=Stop(name="Hub", address="Alexanderplatz"),
        stops=[
            Stop(name="A", address="Kreuzberg", demand_kg=100),
            Stop(name="B", address="Mitte", demand_kg=150),
        ],
        vehicles=[Vehicle(id="V1", capacity_kg=300)],
        simulate_traffic=False,
    )

    response = asyncio.run(run_workflow(request))

    assert response.status == "completed"
    assert len(response.routes) == 1
    assert response.routes[0].total_load_kg == 250
    assert len(response.routes[0].route_coordinates) == 4
    assert response.routes[0].routing_provider == "simulated"
    assert [event.agent for event in response.events] == [
        "planner",
        "executor",
        "reflection",
        "finalizer",
    ]


def test_workflow_reports_unassigned_stops() -> None:
    request = PlanRequest(
        depot=Stop(name="Hub", address="Depot"),
        stops=[Stop(name="Heavy", address="Far", demand_kg=600)],
        vehicles=[Vehicle(id="V1", capacity_kg=300)],
        simulate_traffic=False,
    )

    response = asyncio.run(run_workflow(request))

    assert response.status == "partial"
    assert len(response.unassigned_stops) == 1
    assert response.issues[0].code == "UNASSIGNED_STOPS"


def test_langgraph_contains_the_agent_workflow() -> None:
    node_names = set(workflow_graph.get_graph().nodes)

    assert {
        "planner",
        "executor",
        "weather",
        "disruption_research",
        "traffic",
        "reflection",
        "replanner",
        "finalizer",
    }.issubset(node_names)


def test_langgraph_routes_errors_through_bounded_replanning() -> None:
    state = LogisticsState(
        request=PlanRequest(
            depot=Stop(name="Hub", address="Depot"),
            stops=[Stop(name="A", address="Mitte", demand_kg=10)],
            vehicles=[Vehicle(id="V1", capacity_kg=100)],
        ),
        issues=[ValidationIssue(code="TRAFFIC_CHANGED", message="Heavy traffic")],
    )
    graph_state: WorkflowState = {"logistics": state}

    assert route_after_reflection(graph_state) == "replanner"
    state.replans = settings.max_replans
    assert route_after_reflection(graph_state) == "finalizer"
