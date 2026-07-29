from models.schemas import AgentEvent


def event_timeline(events: list[AgentEvent]) -> list[dict[str, str]]:
    return [
        {
            "agent": event.agent,
            "action": event.action,
            "summary": event.summary,
            "timestamp": event.timestamp.isoformat(),
        }
        for event in events
    ]
