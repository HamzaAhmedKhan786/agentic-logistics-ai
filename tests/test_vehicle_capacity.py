import pytest
from pydantic import ValidationError

from models.schemas import Vehicle


def test_vehicle_capacity_can_be_reduced_below_type_limit() -> None:
    vehicle = Vehicle(id="TRUCK-01", type="truck", capacity_kg=1200)

    assert vehicle.capacity_kg == 1200


def test_vehicle_capacity_cannot_exceed_type_limit() -> None:
    with pytest.raises(ValidationError, match="truck capacity cannot exceed 1500 kg"):
        Vehicle(id="TRUCK-01", type="truck", capacity_kg=1501)
