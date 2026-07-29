from models.schemas import ValidationIssue
from models.state import LogisticsState
from tools.weather import current_berlin_weather


async def run(state: LogisticsState) -> LogisticsState:
    if state.weather_checked:
        return state
    state.weather_checked = True
    state.weather = await current_berlin_weather()
    if state.weather is None:
        return state

    if state.weather.severe:
        visibility = (
            f"{state.weather.visibility_m:.0f} m"
            if state.weather.visibility_m is not None
            else "unknown"
        )
        state.issues.append(
            ValidationIssue(
                code="SEVERE_WEATHER",
                message=(
                    f"Current Berlin weather requires dispatcher review: "
                    f"{state.weather.condition}, gusts "
                    f"{state.weather.wind_gust_kmh:.0f} km/h, visibility "
                    f"{visibility}."
                ),
                severity="error",
            )
        )
    state.emit(
        "weather",
        "observe_current_conditions",
        (
            f"Berlin: {state.weather.condition}, "
            f"{state.weather.temperature_c:.1f}°C, gusts "
            f"{state.weather.wind_gust_kmh:.0f} km/h"
        ),
    )
    return state
