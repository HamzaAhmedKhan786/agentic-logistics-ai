from __future__ import annotations

import json
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import make_asgi_app

from config.llm import llm
from config.logging import configure_logging
from config.metrics import PLAN_DURATION, PLAN_RUNS
from config.settings import settings
from graph.checkpoints import load_checkpoint
from graph.workflow import run_workflow
from models.schemas import HealthResponse, PlanRequest, PlanResponse
from services.event_broker import broker
from services.traffic_monitor import traffic_monitor
from storage.repository import approve_plan, get_plan as get_db_plan, init_database, save_plan


ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "frontend" / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    await init_database()
    yield
    await traffic_monitor.stop_all()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Multi-agent logistics route planning API",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.app_env == "development" else [],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/metrics", make_asgi_app(), name="metrics")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        orchestrator="langgraph",
        llm_provider=llm.provider,
        llm_enabled=llm.enabled,
        location_provider=settings.location_provider,
        routing_provider=settings.routing_provider,
    )


@app.post("/api/plans", response_model=PlanResponse)
async def create_plan(request: PlanRequest) -> PlanResponse:
    started = time.perf_counter()
    response = await run_workflow(request)
    await save_plan(response)
    traffic_monitor.start(response.run_id)
    PLAN_DURATION.observe(time.perf_counter() - started)
    PLAN_RUNS.labels(
        status=response.status, provider=settings.location_provider
    ).inc()
    return response


@app.get("/api/plans/{run_id}")
async def get_plan(run_id: str) -> dict:
    stored = await get_db_plan(run_id)
    if stored:
        return stored
    try:
        return load_checkpoint(run_id)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="Plan not found") from None


@app.post("/api/plans/{run_id}/approve")
async def approve(run_id: str) -> dict:
    approved = await approve_plan(run_id)
    if not approved:
        raise HTTPException(status_code=404, detail="Plan not found")
    await broker.publish(run_id, {"type": "plan_approved", "run_id": run_id})
    return approved


@app.get("/api/plans/{run_id}/events")
async def stream_events(run_id: str) -> StreamingResponse:
    if not await get_db_plan(run_id):
        raise HTTPException(status_code=404, detail="Plan not found")

    async def event_stream():
        yield f"data: {json.dumps({'type': 'connected', 'run_id': run_id})}\n\n"
        async for event in broker.subscribe(run_id):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/workflow")
async def workflow_definition() -> dict:
    return {
        "nodes": [
            "planner",
            "executor",
            "weather",
            "disruption_research",
            "traffic",
            "reflection",
            "replanner",
            "finalizer",
        ],
        "edges": [
            ["planner", "executor"],
            ["executor", "weather"],
            ["weather", "disruption_research"],
            ["disruption_research", "traffic"],
            ["traffic", "reflection"],
            ["reflection", "replanner", "errors and retry budget remains"],
            ["replanner", "executor"],
            ["reflection", "finalizer", "valid or retry budget exhausted"],
        ],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
