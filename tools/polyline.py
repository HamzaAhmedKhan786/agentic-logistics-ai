from models.schemas import Coordinate


def decode_google_polyline(encoded: str) -> list[Coordinate]:
    """Decode Google's encoded polyline format without a provider SDK."""
    coordinates: list[Coordinate] = []
    index = latitude = longitude = 0
    while index < len(encoded):
        deltas: list[int] = []
        for _ in range(2):
            result = shift = 0
            while True:
                value = ord(encoded[index]) - 63
                index += 1
                result |= (value & 0x1F) << shift
                shift += 5
                if value < 0x20:
                    break
            deltas.append(~(result >> 1) if result & 1 else result >> 1)
        latitude += deltas[0]
        longitude += deltas[1]
        coordinates.append(
            Coordinate(latitude=latitude / 1e5, longitude=longitude / 1e5)
        )
    return coordinates


def decode_here_polyline(encoded: str) -> list[Coordinate]:
    """Decode a HERE flexible polyline using HERE's small reference package."""
    import flexpolyline

    decoded = flexpolyline.decode(encoded)
    return [
        Coordinate(latitude=point[0], longitude=point[1])
        for point in decoded
    ]
