from config.settings import settings
from models.schemas import VehicleRoute
from models.state import LogisticsState
from tools.geocoding import geocode_many_real, geocode_real
from tools.optimizer import optimize_routes
from tools.routing import build_provider_legs


async def run(state: LogisticsState) -> LogisticsState:
    depot = await geocode_real(state.request.depot)
    stops = await geocode_many_real(state.request.stops)
    assignments, unassigned, optimizer = optimize_routes(
        depot, stops, state.request.vehicles
    )
    routes: list[VehicleRoute] = []

    for vehicle in state.request.vehicles:
        ordered = assignments[vehicle.id]
        if state.traffic_reroute and len(ordered) > 1:
            ordered = list(reversed(ordered))
        if not ordered:
            continue
        legs, routing_provider, geometry = await build_provider_legs(depot, ordered)
        distance = round(sum(leg.distance_km for leg in legs), 2)
        driving_minutes = sum(leg.duration_minutes for leg in legs)
        service_minutes = sum(stop.service_minutes for stop in ordered)
        routes.append(
            VehicleRoute(
                vehicle_id=vehicle.id,
                stops=ordered,
                legs=legs,
                total_distance_km=distance,
                total_duration_minutes=round(driving_minutes + service_minutes, 1),
                total_load_kg=round(sum(stop.demand_kg for stop in ordered), 2),
                estimated_cost=round(distance * vehicle.cost_per_km, 2),
                route_coordinates=geometry,
                routing_provider=routing_provider,
            )
        )

    state.routes = routes
    state.unassigned_stops = unassigned
    state.emit(
        "executor",
        "execute_tools",
        f"Built {len(routes)} {settings.location_provider} route(s) with {optimizer}; "
        f"{len(unassigned)} stops remain unassigned",
    )
    return state
