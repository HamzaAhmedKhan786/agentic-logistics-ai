import asyncio

from agents import planner_agent, reflection_agent
from models.schemas import PlanRequest, Stop, Vehicle
from models.state import LogisticsState


def make_state() -> LogisticsState:
    return LogisticsState(
        request=PlanRequest(
            depot=Stop(name="Hub", address="Berlin"),
            stops=[Stop(name="A", address="Mitte", demand_kg=50)],
            vehicles=[Vehicle(id="V1", capacity_kg=100)],
            simulate_traffic=False,
        )
    )


def test_planner_emits_structured_strategy() -> None:
    state = asyncio.run(planner_agent.run(make_state()))
    assert state.plan_strategy["strategy"]
    assert isinstance(state.plan_strategy["constraints"], list)
    assert state.events[-1].agent == "planner"


def test_reflection_never_hides_validator_result() -> None:
    state = make_state()
    state = asyncio.run(reflection_agent.run(state))
    assert state.reflection["verdict"] == "accept"
    assert state.events[-1].agent == "reflection"
