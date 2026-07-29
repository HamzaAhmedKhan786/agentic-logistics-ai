# Provider and Production Setup

## Selected development map mode

The current configuration uses the free, no-account map stack:

```dotenv
LOCATION_PROVIDER=simulated
ROUTING_PROVIDER=osrm
OSRM_BASE_URL=https://router.project-osrm.org
TRAFFIC_PROVIDER=synthetic
HERE_API_KEY=
GOOGLE_MAPS_API_KEY=
```

MapLibre and OpenFreeMap provide the visual basemap. The backend supplies stable
demo coordinates, OSRM snaps them to roads and returns road-following geometry,
and the traffic layer remains synthetic. HERE and Google remain optional future
upgrade paths.

## HERE setup

1. Create or sign in to a HERE platform account.
2. Create a project.
3. Add the Geocoding & Search and Routing services.
4. Create an application and generate an API key.
5. Restrict and rotate the key according to your HERE account controls.
6. Configure:

```dotenv
LOCATION_PROVIDER=here
ROUTING_PROVIDER=here
TRAFFIC_PROVIDER=here
HERE_API_KEY=your-key
```

HERE Routing returns flexible polylines. The backend decodes them through
`flexpolyline`, so the map animation follows the road geometry.

## Google Maps Platform setup

1. Create a Google Cloud project.
2. Attach a billing account.
3. Enable **Geocoding API** and **Routes API**.
4. Create an API key in **APIs & Services → Credentials**.
5. Restrict the key to the two enabled APIs and to the backend environment.
6. Configure quotas and billing alerts.
7. Configure:

```dotenv
LOCATION_PROVIDER=google
ROUTING_PROVIDER=google
TRAFFIC_PROVIDER=google
GOOGLE_MAPS_API_KEY=your-key
```

Google Routes returns encoded polylines. The backend decodes the polyline and uses
traffic-aware routing. `TRAFFIC_AWARE_OPTIMAL` and traffic-aware polylines can use
higher-priced SKUs, so review the field mask and routing preference before load.

## What OR-Tools does

OR-Tools is Google's free, open-source optimization toolkit. In this project its
capacitated Vehicle Routing Problem solver:

- assigns stops to vehicles;
- respects vehicle capacities;
- orders stops to reduce distance;
- permits an expensive dropped-stop penalty for infeasible demand;
- limits solve time to two seconds;
- falls back to the greedy planner if the solver is unavailable.

The LLM describes objectives and explains outcomes. OR-Tools performs the numerical
optimization.

## Database

Local development defaults to SQLite:

```dotenv
DATABASE_URL=sqlite+aiosqlite:///./output/logistics.db
```

For an existing local PostgreSQL installation:

```powershell
.\database\scripts\setup.ps1
.\database\scripts\verify.ps1
```

The setup script prints the `DATABASE_URL` value to place in `.env`.

Alternatively, start the bundled PostgreSQL container:

```powershell
docker compose up -d postgres
```

```dotenv
DATABASE_URL=postgresql+asyncpg://logistics:logistics-dev@localhost:5432/logistics
```

Replace development credentials before deployment. Use migrations rather than
`create_all` once the schema is shared by multiple environments.

## Prometheus and Grafana

Start the app on port 8000, then:

```powershell
docker compose up -d prometheus grafana
```

- Prometheus: `http://localhost:9090`
- Prometheus Pushgateway: `http://localhost:9091`
- Grafana: `http://localhost:3000`
- Development Grafana credentials: `admin` / `admin`
- Application metrics: `http://localhost:8000/metrics/`

Grafana automatically provisions the Prometheus data source and the **RouteMind
Operations** dashboard.

## DeepEval with Groq

Install evaluation-only dependencies:

```powershell
pip install -r requirements-eval.txt
```

Configure Groq and opt in:

```dotenv
LLM_PROVIDER=groq
GROQ_API_KEY=your-key
RUN_LLM_EVALS=true
```

Run:

```powershell
deepeval test run tests/evals/test_planner_deepeval.py
```

DeepEval calls an LLM judge and therefore consumes Groq tokens. Deterministic agent
tests remain part of ordinary `pytest`. The evaluation publishes
`logistics_llm_eval_score` to Prometheus Pushgateway, and Grafana displays the
latest score.

## Dispatcher approval and streaming

If replanning changes route order or assignments, the response status becomes
`awaiting_approval`. Approve through the dashboard or:

```http
POST /api/plans/{run_id}/approve
```

Subscribe to monitoring events:

```http
GET /api/plans/{run_id}/events
Accept: text/event-stream
```

## Production leftovers

The current background monitor uses in-process asyncio tasks. Before horizontal
scaling:

1. Move monitoring and replanning to Celery/Dramatiq workers.
2. Use Redis Streams, Kafka, or PostgreSQL notifications for events.
3. Persist traffic observations and plan revisions as separate tables.
4. Add optimistic locking around approvals.
5. Require authentication and organization authorization.
6. Add Alembic migrations and encrypted secret management.
7. Add Loki or OpenSearch if centralized searchable logs are required; Grafana and
   Prometheus currently cover metrics, not durable log storage.
