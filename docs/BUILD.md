# Build and deploy guide

The whole project is one Declarative Automation Bundle: `databricks.yml` (bundle `bluerridge_pm_copilot`, target `demo`) plus `resources/`. This page is the short path; the [implementation plan](superpowers/plans/2026-11-06-bluerridge-pm-copilot.md) has the task-by-task detail.

## Prerequisites

| Need | Value |
|---|---|
| Databricks CLI | v1.20.0 or newer (the version this repo was validated with) |
| Workspace | `https://fevm-mfg-mc-se-sa.cloud.databricks.com` |
| CLI profile | any profile for that workspace; the commands below use `DEFAULT` and always pass `--profile` |
| Catalog | `mfg_mc_se_sa`, which already exists (`CREATE CATALOG` is blocked in this workspace) |
| SQL warehouse | `hobbs`, id `527214d7319cb124`, serverless |
| Local tools | Python 3.10+ (`pip install -e ".[dev]"` for the unit tests), Node.js 18+ (frontend build) |

The bundle variables default to these values: `catalog` = `mfg_mc_se_sa`, `schema_prefix` = `bluerridge`, `warehouse_id` = `527214d7319cb124`.

## Deploy

```bash
databricks bundle validate --profile DEFAULT
databricks bundle deploy -t demo --profile DEFAULT
```

Some steps are not bundle resources and have to happen in a fixed order: the Unity Catalog schemas and Volumes must exist before anything writes to them, the Lakebase instance must exist before its synced tables, and the app's service principal needs its grants after both. Where a step cannot be folded into `bundle deploy`, it is an explicit command in the sequence below.

## Sequence

Each stage reads what the earlier stages wrote.

| # | Stage | Where | Result |
|---|---|---|---|
| 0 | Unity Catalog objects | `00_setup/00_create_schemas_and_volumes.ipynb` | Seven `bluerridge_*` schemas; Volumes `bluerridge_landing.drawings` and `bluerridge_landing.project` |
| 1 | Synthetic data | `01_synthetic_data/` | Project CSVs and drawing PDFs in the two Volumes, plus the planted-flaw ground truth |
| 2 | Lakeflow ingestion | `02_pipelines/`, `resources/pipeline-*.yml` | Bronze and silver tables from Auto Loader + Spark Declarative Pipelines |
| 3 | Document intelligence | `03_doc_intelligence/` | `drawings_parsed`, `drawings_extracted`, `compliance_findings`, `compliance_eval` |
| 4 | Vector Search | `04_vector_search/`, `resources/vector-search.yml` | `code_excerpts` table, endpoint `bluerridge_vs`, index `code_excerpts_vs` |
| 5 | Gold | `05_gold/` | `kpi_daily`, `risk_forecast`, `daily_brief` |
| 6 | Governance | `06_governance/` | Tags, grants and a row filter |
| 7 | Genie Space | `07_genie_agent/`, `resources/genie-space.yml` | Space `bluerridge_pm_copilot` and its Q&A transcript |
| 8 | Lakebase | `08_lakebase/`, `resources/lakebase.yml` | Instance `bluerridge-pm` with synced `kpi_daily`, `compliance_findings`, `risk_forecast` |
| 9 | App | `09_app/`, `resources/app.yml` | The Databricks App (`09_app/deploy.sh`) |

Catalog `mfg_mc_se_sa` is shared with other teams: touch only objects whose schema starts with `bluerridge_`.

## Running a notebook so its outputs are real

Committed notebooks are executed on the workspace as a one-time serverless job run, so the outputs in them are genuine. The recipe, with `00_setup/00_create_schemas_and_volumes.ipynb` as the worked example:

```bash
# 1. Put the notebook in the workspace (a scratch folder is fine)
databricks workspace import /Workspace/Users/<you>/<scratch>/00_setup/00_create_schemas_and_volumes \
  --file 00_setup/00_create_schemas_and_volumes.ipynb --format JUPYTER --overwrite --profile DEFAULT

# 2. Run it once. A notebook_task with no cluster spec runs on serverless compute.
#    submit.json: {"run_name": "...", "tasks": [{"task_key": "main",
#                  "notebook_task": {"notebook_path": "/Workspace/Users/<you>/<scratch>/00_setup/00_create_schemas_and_volumes"}}]}
databricks jobs submit --json @submit.json --profile DEFAULT

# 3. Export the executed notebook, using the task run id from the submit output
databricks jobs export-run <task_run_id> --views-to-export ALL --profile DEFAULT -o json
```

The exported HTML goes to `evidence/notebook_html_exports/<notebook name>.html`. The same run's cell outputs, run id and run URL are recorded in the committed `.ipynb`. A notebook that writes `outputs/...` does so next to itself in the workspace (the working directory of a notebook run is its own folder); copy it back with `databricks workspace export <path> --file <local path> --format AUTO --profile DEFAULT`.

## Gotchas found while building

- `SHOW SCHEMAS ... LIKE` uses `*` as its wildcard and matches `%` literally, so `LIKE 'bluerridge_%'` returns nothing. Use `LIKE 'bluerridge_*'`.
- `databricks bundle validate` accepts any key under `experimental.scripts`, so a passing validate does not prove a lifecycle hook name is real. The top-level `scripts:` block holds named scripts that run on demand with `databricks bundle run <name>`.
