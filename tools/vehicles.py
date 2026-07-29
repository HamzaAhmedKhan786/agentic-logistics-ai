from __future__ import annotations

from models.schemas import Stop, Vehicle


def assign_by_capacity(stops: list[Stop], vehicles: list[Vehicle]) -> tuple[dict[str, list[Stop]], list[Stop]]:
    assignments = {vehicle.id: [] for vehicle in vehicles}
    remaining_capacity = {vehicle.id: vehicle.capacity_kg for vehicle in vehicles}
    unassigned: list[Stop] = []

    for stop in sorted(stops, key=lambda item: item.demand_kg, reverse=True):
        eligible = [
            vehicle
            for vehicle in vehicles
            if remaining_capacity[vehicle.id] >= stop.demand_kg
        ]
        if not eligible:
            unassigned.append(stop)
            continue
        selected = max(eligible, key=lambda vehicle: remaining_capacity[vehicle.id])
        assignments[selected.id].append(stop)
        remaining_capacity[selected.id] -= stop.demand_kg
    return assignments, unassigned
