from config.settings import settings
from models.state import LogisticsState


def should_replan(state: LogisticsState) -> bool:
    hard_errors = any(issue.severity == "error" for issue in state.issues)
    return hard_errors and state.replans < settings.max_replans
