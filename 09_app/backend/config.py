"""Runtime configuration, read from the environment (app.yaml / resource bindings)."""
import os
from pathlib import Path

CATALOG = os.getenv("CATALOG", "mfg_mc_se_sa")
SCHEMA_PREFIX = os.getenv("SCHEMA_PREFIX", "bluerridge")
WAREHOUSE_ID = os.getenv("WAREHOUSE_ID", "527214d7319cb124")
GENIE_SPACE_ID = os.getenv("GENIE_SPACE_ID", "01f1db9edffa1a298195db2806ce45e3")

# Lakebase Autoscaling project bluerridge-pm (see docs/BUILD.md "Lakebase + app").
# PGHOST/PGPORT/PGDATABASE/PGUSER/PGSSLMODE are injected by the platform when the
# `postgres` resource is bound; LAKEBASE_ENDPOINT comes from `valueFrom: postgres`.
LAKEBASE_PROJECT = os.getenv("LAKEBASE_PROJECT", "bluerridge-pm")
LAKEBASE_ENDPOINT = os.getenv(
    "LAKEBASE_ENDPOINT", f"projects/{LAKEBASE_PROJECT}/branches/production/endpoints/primary"
)
LAKEBASE_DATABASE = os.getenv("LAKEBASE_DATABASE", os.getenv("PGDATABASE", "databricks_postgres"))
LAKEBASE_SCHEMA = os.getenv("LAKEBASE_SCHEMA", f"{SCHEMA_PREFIX}_app")

# The demo's "today" (synthetic data is anchored here).
AS_OF_DATE = os.getenv("AS_OF_DATE", "2026-11-06")

# Built SPA (Vite outDir). Not committed; produced by `npm run build`.
STATIC_DIR = Path(os.getenv("STATIC_DIR", str(Path(__file__).resolve().parent.parent / "frontend" / "dist")))
