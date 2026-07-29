from __future__ import annotations

from config.settings import settings
from models.schemas import Stop, Vehicle
from tools.routing import haversine_km, nearest_neighbor
from tools.vehicles import assign_by_capacity


def optimize_routes(
    depot: Stop,
    stops: list[Stop],
    vehicles: list[Vehicle],
) -> tuple[dict[str, list[Stop]], list[Stop], str]:
    """Solve a capacitated VRP; gracefully fall back when OR-Tools is unavailable."""
    if not settings.use_ortools:
        assignments, unassigned = assign_by_capacity(stops, vehicles)
        return {
            vehicle.id: nearest_neighbor(depot, assignments[vehicle.id])
            for vehicle in vehicles
        }, unassigned, "greedy"

    try:
        from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    except ImportError:
        assignments, unassigned = assign_by_capacity(stops, vehicles)
        return {
            vehicle.id: nearest_neighbor(depot, assignments[vehicle.id])
            for vehicle in vehicles
        }, unassigned, "greedy-fallback"

    points = [depot, *stops]
    manager = pywrapcp.RoutingIndexManager(len(points), len(vehicles), 0)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index: int, to_index: int) -> int:
        first = points[manager.IndexToNode(from_index)]
        second = points[manager.IndexToNode(to_index)]
        return int(haversine_km(first, second) * 1000)

    transit_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_index)

    demands = [0, *[round(stop.demand_kg) for stop in stops]]

    def demand_callback(index: int) -> int:
        return demands[manager.IndexToNode(index)]

    demand_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_index,
        0,
        [round(vehicle.capacity_kg) for vehicle in vehicles],
        True,
        "Capacity",
    )

    drop_penalty = 10_000_000
    for node in range(1, len(points)):
        routing.AddDisjunction([manager.NodeToIndex(node)], drop_penalty)

    parameters = pywrapcp.DefaultRoutingSearchParameters()
    parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    parameters.time_limit.FromSeconds(2)
    solution = routing.SolveWithParameters(parameters)
    if solution is None:
        assignments, unassigned = assign_by_capacity(stops, vehicles)
        return assignments, unassigned, "greedy-fallback"

    result = {vehicle.id: [] for vehicle in vehicles}
    visited: set[int] = set()
    for vehicle_index, vehicle in enumerate(vehicles):
        index = routing.Start(vehicle_index)
        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            if node:
                result[vehicle.id].append(stops[node - 1])
                visited.add(node - 1)
            index = solution.Value(routing.NextVar(index))
    unassigned = [stop for index, stop in enumerate(stops) if index not in visited]
    return result, unassigned, "ortools"
