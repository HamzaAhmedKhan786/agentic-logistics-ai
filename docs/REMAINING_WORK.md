# Remaining Work

This document separates prototype-complete features from the work required for a
production logistics system.

## Completed in the current prototype

- HERE flexible-polyline decoding
- Google encoded-polyline decoding
- OR-Tools capacitated vehicle routing with heuristic fallback
- Plan comparison and dispatcher approval endpoint/UI
- SQLAlchemy persistence with SQLite and PostgreSQL configuration
- In-process traffic monitoring and server-sent events
- Structured JSON logs and Prometheus metrics
- Provisioned Grafana dashboard
- Deterministic agent tests and opt-in DeepEval/Groq judge tests

## 1. Industrial road geometry validation

Geometry decoding is implemented. Still add provider contract fixtures, malformed
polyline tests, route-gap detection, and licensing/retention checks.

## 2. Real-time traffic monitoring

**Current state:** seeded traffic, HERE/Google observations, and an in-process
monitor exist. Moving automatic monitoring to durable workers remains.

**How to achieve it:**

1. Store provider observation time and expiry.
2. Poll only active runs through a durable background worker.
3. Enqueue a new plan revision when delay crosses a business threshold.
4. Notify the dispatcher; the existing approval gate accepts the revision.

Do not poll inside the synchronous HTTP request in production.

## 3. Vehicle Routing Problem solver

**Current state:** OR-Tools CVRP with capacity constraints and a two-second solve
limit. Greedy planning is now the fallback.

**How to achieve it:**

1. Build a provider road distance/time matrix instead of Haversine costs.
2. Model time windows, service time, shifts, and vehicle-specific costs.
3. Add benchmark datasets and solver-quality regression tests.

## 4. Targeted replanning

**Current state:** traffic retries reverse stop order; other retries prioritize
larger vehicles.

**How to achieve it:**

1. Create an allowlisted action per validation issue code.
2. Validate LLM decisions with a Pydantic discriminated union.
3. Apply only the selected deterministic action.
4. Compare the new plan with the previous plan before accepting it.
5. Stop when cost or feasibility does not improve.

## 5. Durable workflow execution

**Current state:** durable SQL storage and in-process monitoring exist.

**How to achieve it:**

1. Normalize runs, routes, observations, approvals, events, and versions.
2. Add Redis plus Celery, Dramatiq, or another job worker.
3. Make workflow nodes idempotent.
4. Add cancellation and retry controls.

## 6. Real RAG and Tavily research

**Current state:** policy retrieval uses a small in-memory list. Tavily optionally
searches recent Berlin disruption reports, the LLM structures them, and the
workflow matches named locations to routes. Sources and confidence are retained,
and high-confidence active matches require dispatcher review. A separate no-key
Open-Meteo adapter supplies current Berlin conditions and deterministic severe
weather checks.

**How to achieve it:**

1. Parse company policies and operating documents.
2. Store embeddings in PostgreSQL/pgvector or Qdrant.
3. Return citations with every retrieved policy.
4. Add structured official incident/closure geometry and provider-specific road
   exclusions so confirmed closures are actually avoided.
5. Corroborate Tavily findings across multiple sources before operational use.

## 7. Security and tenant isolation

1. Add OpenID Connect authentication.
2. Scope every run and vehicle to an organization.
3. Move keys to a managed secret store.
4. Add rate limits, strict production CORS, and request-size limits.
5. Redact addresses and prompts from logs.
6. Add audit retention and deletion policies.

## 8. Map and provider production readiness

1. Self-host OpenFreeMap or contract a tile provider for an SLA.
2. Preserve visible OpenStreetMap/OpenMapTiles attribution.
3. Restrict HERE/Google keys by API and server environment.
4. Cache geocodes and distance matrices.
5. Add provider quotas, budget alerts, circuit breakers, and fallback rules.

## Recommended implementation order

1. Vehicle-specific road restrictions, environmental zones, and legal dimensions.
2. Structured official closure geometry and targeted route avoidance.
3. Provider road-time matrices, time windows, shifts, and solver benchmarks.
4. Durable background workers, normalized revisions, and database migrations.
5. Authentication, tenancy, secrets management, and production deployment.
6. Real policy RAG, multi-source disruption corroboration, and centralized logs.
