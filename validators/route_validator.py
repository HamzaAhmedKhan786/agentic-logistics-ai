from models.schemas import ValidationIssue, Vehicle, VehicleRoute


def validate_route(route: VehicleRoute, vehicle: Vehicle) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if route.total_load_kg > vehicle.capacity_kg:
        issues.append(
            ValidationIssue(
                code="CAPACITY_EXCEEDED",
                message=f"{vehicle.id} load exceeds capacity by "
                f"{route.total_load_kg - vehicle.capacity_kg:.1f} kg",
            )
        )
    if route.total_distance_km > vehicle.max_distance_km:
        issues.append(
            ValidationIssue(
                code="MAX_DISTANCE_EXCEEDED",
                message=f"{vehicle.id} route exceeds maximum distance by "
                f"{route.total_distance_km - vehicle.max_distance_km:.1f} km",
            )
        )
    return issues
