\set ON_ERROR_STOP on

SELECT current_database() AS database_name, current_user AS connected_user;

SELECT
    table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name = 'plan_runs';

SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'plan_runs'
ORDER BY ordinal_position;

SELECT COUNT(*) AS stored_plan_count FROM plan_runs;
