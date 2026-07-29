\set ON_ERROR_STOP on

CREATE TABLE IF NOT EXISTS plan_runs (
    run_id VARCHAR(36) PRIMARY KEY,
    status VARCHAR(32) NOT NULL,
    approved BOOLEAN NOT NULL DEFAULT FALSE,
    payload TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_plan_runs_status ON plan_runs (status);
CREATE INDEX IF NOT EXISTS ix_plan_runs_created_at ON plan_runs (created_at DESC);

COMMENT ON TABLE plan_runs IS
    'Durable agentic logistics plan responses and dispatcher approval state.';
