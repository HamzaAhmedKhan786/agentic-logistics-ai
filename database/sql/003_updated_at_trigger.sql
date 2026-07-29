\set ON_ERROR_STOP on

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_plan_runs_updated_at ON plan_runs;

CREATE TRIGGER trg_plan_runs_updated_at
BEFORE UPDATE ON plan_runs
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
