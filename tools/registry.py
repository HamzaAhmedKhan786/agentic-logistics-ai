from tools.geocoding import geocode_many
from tools.rag import retrieve_policies
from tools.routing import build_legs, nearest_neighbor
from tools.vehicles import assign_by_capacity


TOOL_REGISTRY = {
    "geocode_many": geocode_many,
    "retrieve_policies": retrieve_policies,
    "nearest_neighbor": nearest_neighbor,
    "build_legs": build_legs,
    "assign_by_capacity": assign_by_capacity,
}


def get_tool(name: str):
    try:
        return TOOL_REGISTRY[name]
    except KeyError as exc:
        raise ValueError(f"Unknown tool: {name}") from exc
