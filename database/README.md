# PostgreSQL Database Scripts

These scripts create the application role, database, schema, indexes, and
`updated_at` trigger without deleting existing data.

## Requirements

- PostgreSQL is running.
- `psql` is available on `PATH`.
- You know the PostgreSQL administrator password.

On Windows, `psql.exe` is usually under:

```text
C:\Program Files\PostgreSQL\<version>\bin
```

## Automated setup

From the project root:

```powershell
.\database\scripts\setup.ps1
```

Defaults:

- Database: `logistics`
- Application role: `logistics`
- Administrator: `postgres`
- Host: `localhost`
- Port: `5432`

Override them when required:

```powershell
.\database\scripts\setup.ps1 `
  -DatabaseName route_mind `
  -AppUser route_mind_app `
  -AdminUser postgres `
  -HostName localhost `
  -Port 5432
```

The script securely prompts for the application-role password. `psql` may also
prompt for the PostgreSQL administrator password. At completion, it prints the
URL-encoded `DATABASE_URL` value to copy into `.env`.

## Verify

```powershell
.\database\scripts\verify.ps1
```

Enter the application-role password when `psql` prompts. Verification shows:

- Connected database and role
- `plan_runs` table
- Column definitions
- Number of saved plans

## SQL files

- `001_create_database.sql`: creates/updates the role and database.
- `002_schema.sql`: creates the application table and indexes.
- `003_updated_at_trigger.sql`: maintains modification timestamps.
- `verify.sql`: performs read-only checks.

All setup scripts are idempotent and can be rerun. They do not drop the database,
table, or stored plans.
