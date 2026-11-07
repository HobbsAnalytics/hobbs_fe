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
| Local tools | Python 3.10+ (`pip install -e ".[dev]"` for the unit tests), Node.js 18+ (frontend build), `uv` (only to render the evidence HTML, see below) |

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
| 1 | Synthetic data | `01_synthetic_data/`, `resources/job-synthetic-data.yml` | Project CSVs and drawing PDFs in the two Volumes, plus the planted-flaw ground truth. One job, two parallel tasks: `databricks bundle run job_synthetic_data -t demo --profile DEFAULT` |
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

Committed notebooks are executed on the workspace as a one-time serverless job run, and the run's own cell outputs are written into the `.ipynb` by [`scripts/nb_evidence.py`](../scripts/nb_evidence.py) (standard library only). What a reader sees in the notebook is therefore what the run produced. The commands below use `01_synthetic_data/01_generate_project_data.ipynb` as the worked example; change `NB` and `SCRATCH` for another notebook.

```bash
NB=01_synthetic_data/01_generate_project_data      # the notebook, without ".ipynb"
SCRATCH=/Workspace/Users/<you>/_scratch_bluerridge # throwaway workspace folder

# 1. Put the notebook in the scratch folder (import does not create parent folders)
databricks workspace mkdirs $SCRATCH/$(dirname $NB) --profile DEFAULT
databricks workspace import $SCRATCH/$NB --file $NB.ipynb --format JUPYTER --overwrite --profile DEFAULT

# 2. Run it once. A notebook_task with no cluster spec runs on serverless compute, and `jobs submit`
#    waits for the run to finish (about a minute for a small notebook). submit.json:
#    {"run_name": "...", "tasks": [{"task_key": "main", "notebook_task": {"notebook_path": "<$SCRATCH/$NB>"}}]}
databricks jobs submit --json @submit.json --profile DEFAULT -o json > result.json

# 3. Export the run's record of the executed notebook, using the TASK run id (.tasks[0].run_id)
read -r RUN TASK URL < <(python3 -c "import json; d=json.load(open('result.json')); print(d['run_id'], d['tasks'][0]['run_id'], d['run_page_url'])")
databricks jobs export-run $TASK --views-to-export ALL --profile DEFAULT -o json > export.json

# 4. Write that run's real outputs, run id and run URL into the notebook
python3 -I scripts/nb_evidence.py export.json $NB.ipynb --run-id $RUN --task-run-id $TASK --run-url "$URL"

# 5. Render a readable HTML page for the evidence folder. uv fetches nbconvert on the fly (a system
#    python3 refuses `pip install` under PEP 668); in a virtualenv with nbconvert, drop the "uv run" prefix.
uv run --no-project --with nbconvert python -m nbconvert --to html $NB.ipynb --output-dir evidence/notebook_html_exports

# 6. Pull back the files the notebook wrote to outputs/, and drop the exec bit the export adds
databricks workspace export $SCRATCH/$(dirname $NB)/outputs/<file> --file $(dirname $NB)/outputs/<file> --format AUTO --profile DEFAULT
chmod 644 $(dirname $NB)/outputs/*

# 7. Remove the scratch folder (the run itself stays exportable)
databricks workspace delete $SCRATCH --recursive --profile DEFAULT
```

Things the recipe depends on:

- **Why step 4 exists.** The HTML that `jobs export-run` returns carries the executed notebook as a base64 blob, so the printed text and tables in it cannot be read as text. `nb_evidence.py` decodes the blob and writes the outputs into the `.ipynb` as plain JSON. The HTML to commit is the one `nbconvert` renders from that enriched notebook in step 5, not the raw run page (`nb_evidence.py --html` can still save the raw page).
- **The notebook must not change between steps 1 and 4.** The tool compares every code cell's source with the run's and stops on a mismatch (markdown cells are only checked to be markdown, so an edit to prose goes unnoticed); after any edit, re-import and re-run.
- **Supported outputs** are stdout (`print`) and `display(df)` tables. Any other output type (images, HTML, errors) makes the tool stop rather than drop it silently.
- **`outputs/` is relative.** A notebook run uses its own folder as the working directory, so `outputs/...` lands next to the workspace notebook. The scratch folder has no `outputs/` directory, so notebooks create it themselves.
- **A notebook that imports a module from its own folder** (`02_generate_drawings.ipynb` imports `02_generate_drawings.py`) needs that file next to it in step 1: `databricks workspace import $SCRATCH/$NB.py --file $NB.py --format AUTO --overwrite --profile DEFAULT`. A `.py` without the `# Databricks notebook source` header lands as a workspace file (`workspace list` shows `FILE`), and the notebook puts its working directory on `sys.path`. A bundle deploy uploads the module the same way.

## Gotchas found while building

- `databricks workspace export` writes files with the exec bit (mode 755). `chmod 644` anything under `outputs/` before `git add`.
- `SHOW SCHEMAS ... LIKE` uses `*` as its wildcard and matches `%` literally, so `LIKE 'bluerridge_%'` returns nothing. Use `LIKE 'bluerridge_*'`.
- `databricks bundle validate` accepts any key under `experimental.scripts`, so a passing validate does not prove a lifecycle hook name is real. The top-level `scripts:` block holds named scripts that run on demand with `databricks bundle run <name>`.
