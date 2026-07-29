import asyncio
from collections import defaultdict


class EventBroker:
    def __init__(self) -> None:
        self.queues: dict[str, list[asyncio.Queue]] = defaultdict(list)

    async def publish(self, run_id: str, event: dict) -> None:
        for queue in self.queues[run_id]:
            await queue.put(event)

    async def subscribe(self, run_id: str):
        queue: asyncio.Queue = asyncio.Queue()
        self.queues[run_id].append(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self.queues[run_id].remove(queue)


broker = EventBroker()
