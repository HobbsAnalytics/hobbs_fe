# Unity Catalog bootstrap: schemas and Volumes

Written by `00_setup/00_create_schemas_and_volumes.ipynb` on 2026-11-06 23:32 UTC as joseph.hobbs@databricks.com.

## Schemas: `SHOW SCHEMAS IN mfg_mc_se_sa LIKE 'bluerridge_*'` returned 7 rows

| Schema | Owner | Comment |
|---|---|---|
| `mfg_mc_se_sa.bluerridge_agents` | joseph.hobbs@databricks.com | Genie Agent and Vector Search artifacts (code excerpts, prompt configs) |
| `mfg_mc_se_sa.bluerridge_app` | joseph.hobbs@databricks.com | Databricks App working tables, if any |
| `mfg_mc_se_sa.bluerridge_bronze_drawings` | joseph.hobbs@databricks.com | Bronze: raw drawing PDF binaries plus Auto Loader metadata |
| `mfg_mc_se_sa.bluerridge_bronze_project` | joseph.hobbs@databricks.com | Bronze: raw project tables (schedule, cost, NCRs, change orders, safety log, daily reports) |
| `mfg_mc_se_sa.bluerridge_gold_pm` | joseph.hobbs@databricks.com | Gold: PM-facing aggregates (compliance findings, KPIs, risk forecast, daily brief) |
| `mfg_mc_se_sa.bluerridge_landing` | joseph.hobbs@databricks.com | Raw landing zone: Volumes holding the drawing PDFs and the project CSVs |
| `mfg_mc_se_sa.bluerridge_silver_engineering` | joseph.hobbs@databricks.com | Silver: cleaned project tables plus parsed and extracted drawings |

## Volumes in `mfg_mc_se_sa.bluerridge_landing`

| Volume | Type | Path | Comment |
|---|---|---|---|
| `drawings` | MANAGED | `/Volumes/mfg_mc_se_sa/bluerridge_landing/drawings` | Synthetic engineering drawing PDFs (ISO, P&ID, GA, spec sheets) |
| `project` | MANAGED | `/Volumes/mfg_mc_se_sa/bluerridge_landing/project` | Synthetic project data CSVs (schedule, cost, NCRs, change orders, safety log, daily reports) |
