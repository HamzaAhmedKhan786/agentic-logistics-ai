from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone

from config.metrics import ACTIVE_MONITORS
from config.settings import settings
from services.event_broker import broker


class TrafficMonitor:
    def __init__(self) -> None:
        self.tasks: dict[str, asyncio.Task] = {}

    def start(self, run_id: str) -> None:
        if run_id in self.tasks:
            return
        self.tasks[run_id] = asyncio.create_task(self._monitor(run_id))
        ACTIVE_MONITORS.inc()

    async def _monitor(self, run_id: str) -> None:
        try:
            while True:
                await asyncio.sleep(settings.traffic_poll_seconds)
                await broker.publish(
                    run_id,
                    {
                        "type": "traffic_observation",
                        "run_id": run_id,
                        "level": random.choice(["clear", "light", "moderate", "heavy"]),
                        "provider": settings.traffic_provider,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
        finally:
            ACTIVE_MONITORS.dec()
            self.tasks.pop(run_id, None)

    async def stop_all(self) -> None:
        tasks = list(self.tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


traffic_monitor = TrafficMonitor()
