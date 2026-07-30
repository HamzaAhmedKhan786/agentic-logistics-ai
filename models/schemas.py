from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


class VehicleType(StrEnum):
    VAN = "van"
    TRUCK = "truck"
    BIKE = "bike"
    EV = "ev"


VEHICLE_CAPACITY_LIMITS_KG = {
    VehicleType.BIKE: 40,
    VehicleType.EV: 300,
    VehicleType.VAN: 350,
    VehicleType.TRUCK: 1500,
}


class Stop(BaseModel):
    name: str
    address: str
    demand_kg: float = Field(default=0, ge=0)
    service_minutes: int = Field(default=10, ge=0)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class Vehicle(BaseModel):
    id: str
    type: VehicleType = VehicleType.VAN
    capacity_kg: float = Field(gt=0)
    cost_per_km: float = Field(default=1.0, gt=0)
    max_distance_km: float = Field(default=500, gt=0)

    @model_validator(mode="after")
    def enforce_type_capacity_limit(self) -> "Vehicle":
        maximum = VEHICLE_CAPACITY_LIMITS_KG[self.type]
        if self.capacity_kg > maximum:
            raise ValueError(
                f"{self.type.value} capacity cannot exceed {maximum} kg"
            )
        return self


class PlanRequest(BaseModel):
    depot: Stop
    stops: list[Stop] = Field(min_length=1, max_length=50)
    vehicles: list[Vehicle] = Field(min_length=1)
    objective: str = "Minimize distance while respecting vehicle capacity"
    simulate_traffic: bool = True
    traffic_seed: int | None = None

    @model_validator(mode="after")
    def ensure_unique_vehicle_ids(self) -> "PlanRequest":
        ids = [vehicle.id for vehicle in self.vehicles]
        if len(ids) != len(set(ids)):
            raise ValueError("Vehicle IDs must be unique")
        return self


class RouteLeg(BaseModel):
    origin: str
    destination: str
    distance_km: float
    duration_minutes: float


class Coordinate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class VehicleRoute(BaseModel):
    vehicle_id: str
    stops: list[Stop]
    legs: list[RouteLeg]
    total_distance_km: float
    total_duration_minutes: float
    total_load_kg: float
    estimated_cost: float
    route_coordinates: list[Coordinate] = []
    routing_provider: str = "simulated"
    traffic_level: str = "clear"
    traffic_delay_minutes: float = 0


class ValidationIssue(BaseModel):
    code: str
    message: str
    severity: str = "error"


class DisruptionSignal(BaseModel):
    title: str
    summary: str
    affected_locations: list[str] = []
    disruption_type: str = "other"
    status: str = "unverified"
    confidence: float = Field(default=0, ge=0, le=1)
    source_url: str
    published_at: str | None = None
    affected_vehicle_ids: list[str] = []


class WeatherSnapshot(BaseModel):
    location: str = "Berlin"
    observed_at: str
    temperature_c: float
    apparent_temperature_c: float
    precipitation_mm: float
    snowfall_cm: float
    wind_speed_kmh: float
    wind_gust_kmh: float
    visibility_m: float | None = None
    weather_code: int
    condition: str
    severe: bool = False
    source: str = "Open-Meteo"


class AgentEvent(BaseModel):
    agent: str
    action: str
    summary: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PlanResponse(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    status: str
    objective: str
    routes: list[VehicleRoute]
    unassigned_stops: list[Stop] = []
    issues: list[ValidationIssue] = []
    disruptions: list[DisruptionSignal] = []
    weather: WeatherSnapshot | None = None
    events: list[AgentEvent] = []
    replans: int = 0
    summary: str
    location_provider: str = "simulated"
    comparison: dict = {}
    approval_required: bool = False
    approved: bool = False


class HealthResponse(BaseModel):
    status: str
    orchestrator: str = "langgraph"
    llm_provider: str
    llm_enabled: bool
    location_provider: str
    routing_provider: str
