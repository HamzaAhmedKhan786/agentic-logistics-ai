from models.schemas import VehicleRoute


def compare_plans(
    baseline: list[VehicleRoute],
    candidate: list[VehicleRoute],
) -> dict:
    if not baseline:
        return {"changed": False, "improved": True, "reason": "initial plan"}
    old_distance = sum(route.total_distance_km for route in baseline)
    new_distance = sum(route.total_distance_km for route in candidate)
    old_duration = sum(route.total_duration_minutes for route in baseline)
    new_duration = sum(route.total_duration_minutes for route in candidate)
    signature = lambda routes: {
        route.vehicle_id: [stop.name for stop in route.stops] for route in routes
    }
    sequence_changed = signature(baseline) != signature(candidate)
    return {
        "changed": sequence_changed,
        "assignments_changed": {
            vehicle: set(signature(baseline).get(vehicle, []))
            != set(signature(candidate).get(vehicle, []))
            for vehicle in set(signature(baseline)) | set(signature(candidate))
        },
        "old_distance_km": round(old_distance, 2),
        "new_distance_km": round(new_distance, 2),
        "old_duration_minutes": round(old_duration, 1),
        "new_duration_minutes": round(new_duration, 1),
        "distance_delta_km": round(new_distance - old_distance, 2),
        "duration_delta_minutes": round(new_duration - old_duration, 1),
        "improved": new_duration < old_duration,
    }
