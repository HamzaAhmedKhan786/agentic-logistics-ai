from __future__ import annotations

from dataclasses import dataclass, field

from models.schemas import (
    AgentEvent,
    DisruptionSignal,
    PlanRequest,
    Stop,
    ValidationIssue,
    VehicleRoute,
    WeatherSnapshot,
)


@dataclass
class LogisticsState:
    request: PlanRequest
    routes: list[VehicleRoute] = field(default_factory=list)
    unassigned_stops: list[Stop] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)
    events: list[AgentEvent] = field(default_factory=list)
    replans: int = 0
    status: str = "planning"
    summary: str = ""
    plan_strategy: dict = field(default_factory=dict)
    reflection: dict = field(default_factory=dict)
    traffic_reroute: bool = False
    baseline_routes: list[VehicleRoute] = field(default_factory=list)
    comparison: dict = field(default_factory=dict)
    disruptions: list[DisruptionSignal] = field(default_factory=list)
    disruptions_checked: bool = False
    weather: WeatherSnapshot | None = None
    weather_checked: bool = False

    def emit(self, agent: str, action: str, summary: str) -> None:
        from config.metrics import AGENT_CALLS

        self.events.append(AgentEvent(agent=agent, action=action, summary=summary))
        AGENT_CALLS.labels(agent=agent, result="success").inc()
