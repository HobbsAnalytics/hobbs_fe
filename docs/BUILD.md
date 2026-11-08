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
| 2 | Lakeflow ingestion | `02_pipelines/`, `resources/pipeline-*.yml` | Bronze and silver tables from Auto Loader + Spark Declarative Pipelines. Project data: one serverless pipeline, 6 bronze streaming tables and 6 silver materialized views, after the stage 1 CSVs exist: `databricks bundle run pipeline_project -t demo --profile DEFAULT`. Drawings: a second pipeline, 1 bronze streaming table (`raw_files`, the PDFs as bytes) and 1 silver materialized view (`drawings_raw_tracking`), after the stage 1 PDFs exist: `databricks bundle run pipeline_drawings -t demo --profile DEFAULT` |
| 3 | Document intelligence | `03_doc_intelligence/` | `drawings_parsed`, `drawings_extracted`, `compliance_findings`, `compliance_eval` |
| 4 | Vector Search | `04_vector_search/`, `resources/vector-search.yml` | `code_excerpts` table, endpoint `bluerridge_vs`, index `code_excerpts_vs` |
| 5 | Gold | `05_gold/` | `kpi_daily`, `risk_forecast`, `daily_brief` |
| 6 | Governance | `06_governance/` | Tags, a row filter on `gold_pm.drawing_register`, lineage evidence; grants are in `grants.sql` (see "Governance follow-ups") |
| 7 | Genie Space | `07_genie_agent/`, `resources/genie-space.yml` | Genie Space "Blue Ridge LNG — PM Co-Pilot (synthetic)" (bundle resource `bluerridge_pm_copilot`) and its Q&A transcript |
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
#    (a notebook that calls AI functions also needs "disable_auto_optimization": true on the task, see Gotchas)
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

## Genie space

- **Space id:** `01f1db9edffa1a298195db2806ce45e3` (committed in `07_genie_agent/outputs/space_id.txt`; an id is not a secret). Title "Blue Ridge LNG — PM Co-Pilot (synthetic)", warehouse `hobbs`.
- **How it is created:** `bundle schema` in CLI v1.20.0 defines `genie_spaces` (grep the output for `genie`), so `resources/genie-space.yml` declares the space and `databricks bundle deploy -t demo --profile DEFAULT` creates it. The body comes from `07_genie_agent/genie_space.geniespace.json`, which `python3 -I 07_genie_agent/build_space.py` generates: 11 curated tables with descriptions and synonyms, one general instruction block, and the 10 curated example SQLs. The same script runs every verified SQL on the warehouse and writes `sample_questions.md`, `heldout_questions.md` and `benchmark_expected.json`, so expected answers are query results, not typed numbers. Create the folder named by `parent_path` first (`databricks workspace mkdirs /Workspace/Users/<you>/genie_spaces`).
- **Idempotent re-apply:** `07_genie_agent/01_create_space.ipynb` pages through the workspace's Genie spaces, finds this exact title, `PATCH`es the same definition (or `POST`s a new space if the bundle has not been deployed), asserts the five held-out questions are not in the space, and writes `space_id.txt`. It never touches another space. When running it per the recipe above, upload the definition next to the notebook as `genie_space.json` (the workspace refuses to import a file ending in `.geniespace.json`) plus `benchmark_expected.json`.
- **Benchmark:** `02_run_sample_qa.ipynb` asks 15 questions (10 curated, 5 held-out) as fresh conversations through the Genie Conversation API and writes `evidence/genie_qa_transcript.md`. It calls the REST endpoints through `WorkspaceClient.api_client` because the serverless SDK has no `w.genie`. Both notebooks ran as one-time serverless `jobs submit` runs (`07_genie_agent/outputs/submit_payloads/`); the run as the submitting user was accepted by the Conversation API, so no local-script fallback was needed. The notebook writes the transcript into its own `outputs/` folder; pull it back with `databricks workspace export` and copy it to `evidence/`.
- **App calls run as the signed-in PM.** The app calls the space on behalf of the user (OBO, `user_api_scopes: [dashboards.genie]`), so each query runs with that PM's own Unity Catalog permissions, including the `drawing_register` row filter, not as the app's service principal.

## Vector Search: bundle resources, with one ordering rule

`bundle schema` in CLI v1.20.0 defines `vector_search_endpoints` and `vector_search_indexes` (grep the output for `vector_search`), and `bundle validate` accepts them, so `resources/vector-search.yml` declares endpoint `bluerridge_vs` (STANDARD) and Delta Sync index `code_excerpts_vs` as ordinary bundle resources. No SDK-only path was needed. Order: run `04_vector_search/01_load_code_excerpts.ipynb` first (the index needs the `code_excerpts` table, with Change Data Feed on, to exist), then `bundle deploy`, then `02_create_endpoint_and_index.ipynb`, which reuses the endpoint and index (creating them through the SDK only if missing), triggers a sync, waits for rows indexed = table rows, and runs the smoke test. Right after deploy the endpoint reads ONLINE while the index can stay "pending endpoint provisioning" for several minutes. The excerpt files are validated locally with `uv run --no-project --with pytest --with pyyaml python -m pytest 04_vector_search/tests`.

## Governance follow-ups (Task 24 and group cleanup)

- **App service principal, after `databricks bundle deploy`:** fill `{app_sp}` in `06_governance/grants.sql` (USE SCHEMA + SELECT on `bluerridge_gold_pm` and `bluerridge_agents`, READ VOLUME on `bluerridge_landing.drawings`; USE CATALOG needs the catalog owner) **and** add the row-filter mapping, otherwise the app sees 0 rows of `drawing_register`: `INSERT INTO mfg_mc_se_sa.bluerridge_agents.discipline_access VALUES ('<app sp application id>', '*')`.
- **Groups:** workspace-local groups are rejected by Unity Catalog grants (`PRINCIPAL_DOES_NOT_EXIST`), so none exist. If an account admin supplies `bluerridge-pm` / `bluerridge-engineers`, run `06_governance/apply.ipynb` with the widgets `pm_group` / `engineer_group`. To remove them later: `REVOKE` the same privileges, then ask the account admin to delete the groups.
- **Tags:** the account's governed tags own the keys `layer`, `sensitivity`, `data_class`, `domain`; the project uses `br_layer`, `br_sensitivity`, `br_data_class`, `br_domain`, `synthetic`.
- **Filters:** never attach a row filter or mask to `kpi_daily`, `compliance_findings`, `risk_forecast` or a pipeline input (Lakebase sync and the notebooks would break). Only `drawing_register` carries one.

## Gotchas found while building

- `databricks workspace export` writes files with the exec bit (mode 755). `chmod 644` anything under `outputs/` before `git add`.
- `SHOW SCHEMAS ... LIKE` uses `*` as its wildcard and matches `%` literally, so `LIKE 'bluerridge_%'` returns nothing. Use `LIKE 'bluerridge_*'`.
- Auto Loader's `binaryFile` format has a fixed schema: it rejects `cloudFiles.schemaEvolutionMode=rescue` (`CF_UNSUPPORTED_SCHEMA_EVOLUTION_MODE`; use `none`) and adds no `_rescued_data` column, so a malformed file is an ordinary row. `pipeline_drawings.py` sets `_rescued_data` itself for files without the `%PDF-` header. A streaming table also keeps the row of a source file that is later deleted; only a full refresh removes it.
- A failed serverless notebook task is retried automatically (`attempt_number` 1 in `databricks jobs get-run`), and the retry runs the whole notebook again, AI calls included. For a notebook that calls an AI function (`03_doc_intelligence/01_parse_drawings.ipynb` bills about 1,370 pages per run) put `"disable_auto_optimization": true` on the task in the `jobs submit` JSON; the bundle schema has the same field for job tasks. `jobs submit` also stops waiting after 20 minutes (`--timeout`): for a longer notebook use `--no-wait` and poll `databricks jobs get-run`.
- `databricks bundle validate` accepts any key under `experimental.scripts`, so a passing validate does not prove a lifecycle hook name is real. The top-level `scripts:` block holds named scripts that run on demand with `databricks bundle run <name>`.
