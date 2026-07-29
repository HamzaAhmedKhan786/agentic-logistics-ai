from prometheus_client import Counter, Gauge, Histogram


PLAN_RUNS = Counter(
    "logistics_plan_runs_total", "Plan workflow runs", ["status", "provider"]
)
PLAN_DURATION = Histogram(
    "logistics_plan_duration_seconds", "End-to-end workflow duration"
)
AGENT_CALLS = Counter(
    "logistics_agent_calls_total", "Agent executions", ["agent", "result"]
)
REPLANS = Counter(
    "logistics_replans_total", "Replanning attempts", ["reason"]
)
ACTIVE_MONITORS = Gauge(
    "logistics_active_traffic_monitors", "Active background traffic monitors"
)
LLM_FALLBACKS = Counter(
    "logistics_llm_fallbacks_total", "LLM calls using deterministic fallback", ["provider"]
)
