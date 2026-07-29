import asyncio

from graph.workflow import run_workflow
from models.schemas import PlanRequest, Stop, Vehicle


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
