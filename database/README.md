# Database Layer

## Schema

Apply the warehouse DDL:

```bash
mysql -u root -p < sql/schema/001_olist_mysql_schema.sql
```

## Architecture

| Module | Role |
|--------|------|
| `connection.py` | SQLAlchemy `db` extension, session lifecycle |
| `repository.py` | Read-only SQL for KPIs and charts |

## Connection

Configured via `.env` → `config.Config.SQLALCHEMY_DATABASE_URI`.

The **services** layer uses `AnalyticsRepository` when MySQL is populated; otherwise it falls back to `data/cleaned/*.csv`.
