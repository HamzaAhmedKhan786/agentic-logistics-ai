from models.schemas import Stop
from tools.routing import build_legs, haversine_km
from tools.polyline import decode_google_polyline


def test_haversine_and_round_trip_legs() -> None:
    depot = Stop(name="Depot", address="A", latitude=52.52, longitude=13.405)
    stop = Stop(name="Stop", address="B", latitude=52.5, longitude=13.4)

    assert 2 < haversine_km(depot, stop) < 3
    legs = build_legs(depot, [stop])
    assert len(legs) == 2
    assert legs[0].origin == "Depot"
    assert legs[1].destination == "Depot"


def test_decodes_google_route_geometry() -> None:
    points = decode_google_polyline("_p~iF~ps|U_ulLnnqC_mqNvxq`@")
    assert len(points) == 3
    assert points[0].latitude == 38.5
    assert points[0].longitude == -120.2
