# Backend Migrations

Alembic migrations define the PostgreSQL schema used by collection, backfill, recovery, and dashboard tasks.

Local commands from `backend/`:

```sh
uv run alembic upgrade head
uv run alembic downgrade base
```
