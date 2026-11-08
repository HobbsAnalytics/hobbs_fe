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
| 8 | Lakebase | `08_lakebase/`, `resources/lakebase.yml` | Lakebase project `bluerridge-pm` (bundle `postgres_projects`) with the five hot-path tables synced into Postgres schema `bluerridge_app` (bundle `postgres_synced_tables`): `kpi_daily`, `compliance_findings`, `risk_forecast`, `schedule_overdue`, `daily_brief`. `01_create_instance.ipynb` confirms state, row counts and latency; `app_grants.sql` is run after the app exists |
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

## Lakebase + app

**Flavor and how it is declared.** The "instance" `bluerridge-pm` is a Lakebase **Autoscaling** project (one `production` branch, one `primary` read-write endpoint, Postgres 17), not a Provisioned `database_instances` instance. Evidence for the choice: (a) `databricks bundle schema` on CLI v1.20.0 defines `postgres_projects`, `postgres_branches`, `postgres_endpoints`, `postgres_databases`, `postgres_catalogs` and `postgres_synced_tables` as well as the older `database_instances` / `synced_database_tables`; (b) the current Lakebase guidance treats Provisioned as retired and says the legacy `synced_database_tables` resource fails on current Lakebase, and a Databricks App binds Lakebase through the `postgres` resource key (`branch` + `database`), which targets Autoscaling projects (the old `database` key, `instance_name`, is deprecated). Both the project and the five synced tables deploy as ordinary bundle resources from `resources/lakebase.yml` with `databricks bundle deploy -t demo --profile DEFAULT`, so no SDK-only path is needed and no YAML is dead. `01_create_instance.ipynb` only confirms their state. (The `postgres_synced_tables` resource is newer than some skill docs say; it validated, deployed and produced five online tables in this workspace.)

**Capacity.** The Autoscaling floor is 0.5 CU; the project pins the endpoint to 1 CU min and max (`default_endpoint_settings`), the closest match to the "CU_1" in the plan. Postgres database `databricks_postgres`, schema `bluerridge_app` (created by the synced tables). Endpoint host and counts are in `08_lakebase/outputs/synced_tables_listing.md`.

**Synced tables (SNAPSHOT).** Source `mfg_mc_se_sa.bluerridge_gold_pm.<t>` becomes UC table `mfg_mc_se_sa.bluerridge_app.<t>_synced` and Postgres table `bluerridge_app.<t>_synced`, for the five tables above. SNAPSHOT because the gold tables are rewritten with `CREATE OR REPLACE` and have no Change Data Feed (TRIGGERED and CONTINUOUS need it). Each synced table has its own small managed pipeline in `mfg_mc_se_sa.bluerridge_app`. **Refresh (Task 24):** after any gold refresh, re-sync, for example by starting an update of each synced table's pipeline (`databricks postgres get-synced-table synced_tables/mfg_mc_se_sa.bluerridge_app.<t>_synced` shows `status.pipeline_id`; `databricks pipelines start-update <pipeline_id> --profile DEFAULT`), then re-run `08_lakebase/app_grants.sql` if a table was recreated. **`drawing_register` is never synced:** it has a Unity Catalog row filter that does not propagate to a Postgres copy; the app reads it through the SQL warehouse.

**App resource binding (Task 24, `resources/app.yml`).**

```yaml
resources:
  - name: postgres                      # the resource key; app.yaml reads it with `valueFrom: postgres`
    postgres:
      branch: projects/bluerridge-pm/branches/production
      database: projects/bluerridge-pm/branches/production/databases/databricks-postgres
      permission: CAN_CONNECT_AND_CREATE
```

The app also needs `postgres` in its `user_api_scopes`/scopes list only if it connects as the signed-in user; the plan has the app connect as its service principal, so the binding above is enough.

**How the app gets credentials (Task 19 implements this).** The platform injects `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER` (the app service principal's client id), `PGSSLMODE` and, with `env: - name: LAKEBASE_ENDPOINT / valueFrom: postgres`, the endpoint path `projects/bluerridge-pm/branches/production/endpoints/primary`. There is no static password: the backend calls `WorkspaceClient().postgres.generate_database_credential(endpoint=os.environ["LAKEBASE_ENDPOINT"]).token` (an OAuth token valid for about an hour) and passes it as the psycopg `password` with `sslmode=require`. Refresh it before expiry (every 30 to 40 minutes, or on a new pooled connection) and retry once on a connection error. Queries use the schema-qualified names `bluerridge_app.kpi_daily_synced` and so on. The notebook proves this exact pattern, with the signed-in user instead of the SP.

**Grant steps and ordering (the first-boot `42501`).** Binding the database lets the SP connect and create its own objects, but not read schema `bluerridge_app`, which the sync writer owns. Order:

1. `databricks bundle deploy -t demo --profile DEFAULT` (project, synced tables, then the app, which creates the SP).
2. Wait for the five synced tables to be online (`01_create_instance.ipynb`, or `get-synced-table`).
3. Get the SP client id: `databricks apps get <app> --profile DEFAULT -o json`, field `service_principal_client_id`.
4. If `databricks postgres list-roles projects/bluerridge-pm/branches/production` shows no role for it yet, create one (command in the header of `08_lakebase/app_grants.sql`; the role id is `sp-<client id>`, the Postgres role name is the bare client id).
5. Run `08_lakebase/app_grants.sql` as the project owner with `${APP_SP_ROLE}` replaced by the client id: generate a credential with `databricks postgres generate-database-credential projects/bluerridge-pm/branches/production/endpoints/primary --profile DEFAULT -o json`, then connect with psql or psycopg to the endpoint host, database `databricks_postgres`, user = your email, and run the file. It grants CONNECT on the database, USAGE on the schema and SELECT on the five tables. It does **not** use `ALTER DEFAULT PRIVILEGES` (the owner cannot set it for the sync writer role); re-run the file if a re-sync recreates a table.
6. Only then start or restart the app.

The statements in `app_grants.sql` were dry-run in a rolled-back transaction against the live endpoint (with the owner's own role in place of the placeholder), so the syntax is verified; the real SP role does not exist until the app does.

**Cost and stopping it after the roleplay.** The endpoint is a fixed 1 CU and its scale-to-zero suspend timeout is 86400 s, so an idle project keeps one CU running for up to a day after the last connection. The five snapshot pipelines only run when a sync is triggered. To save cost sooner:

```bash
# shorten the idle timeout (compute suspends 5 minutes after the last connection and wakes in about a second)
databricks postgres update-endpoint projects/bluerridge-pm/branches/production/endpoints/primary spec.suspend_timeout_duration \
  --json '{"spec":{"suspend_timeout_duration":"300s"}}' --profile DEFAULT
# or switch the compute off completely (re-enable with "disabled": false)
databricks postgres update-endpoint projects/bluerridge-pm/branches/production/endpoints/primary spec.disabled \
  --json '{"spec":{"disabled":true}}' --profile DEFAULT
# delete everything when the demo is retired: synced tables first, then the project (permanent, data included)
databricks postgres delete-synced-table synced_tables/mfg_mc_se_sa.bluerridge_app.<t>_synced --profile DEFAULT   # five times
databricks postgres delete-project projects/bluerridge-pm --profile DEFAULT
```

If the project is deleted outside the bundle, remove `resources/lakebase.yml` from `databricks.yml` (or run `databricks bundle destroy`, which also removes the other resources) before the next `bundle deploy`, otherwise it recreates them. Only `bluerridge-pm` belongs to this project; other Lakebase instances and projects in the workspace are not ours.

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

## App build and deploy (Task 17 scaffold)

**Layout.** `09_app/` is the app's `source_code_path`: `app.yaml` (uvicorn `backend.main:app`, port `${DATABRICKS_APP_PORT:-8000}`), `requirements.txt`, `backend/` (FastAPI) and `frontend/` (React 18 + Vite + TS + Tailwind). Vite builds to `09_app/frontend/dist`; FastAPI serves it (static assets plus an `index.html` fallback for client routes; `/health` and `/api/*` keep priority and an unknown `/api/*` path is a 404, not the SPA).

**Deploy order.** The build output is git-ignored, so build first, then deploy:

```bash
cd 09_app/frontend && npm ci && npm run build      # produces 09_app/frontend/dist
cd ../.. && databricks bundle validate --profile DEFAULT
databricks bundle deploy -t demo --profile DEFAULT  # uploads dist via databricks.yml sync.include
# first deploy only: do the app service principal grants (see "Lakebase + app" and the governance section), then
databricks bundle run pm_copilot_app -t demo --profile DEFAULT   # starts the app (or: databricks apps deploy)
```

**Why `sync.include`.** `bundle deploy` skips git-ignored files, so `databricks.yml` has `sync.include: [09_app/frontend/dist/**]`. `databricks bundle sync --dry-run` lists `09_app/frontend/dist/index.html` and `dist/assets/*` for upload when the build exists (and nothing under `node_modules`). If `dist/` is missing the deployed app still answers `/health` but `/` returns 404 "Frontend build not found".

**Local dev.** `cd 09_app && pip install -r requirements.txt && uvicorn backend.main:app --reload` (API on :8000) and `cd 09_app/frontend && npm run dev` (Vite on :3000, proxies `/api` to :8000). Tests: `pytest 09_app/backend/tests -q` and `cd 09_app/frontend && npx vitest run`.

**App resource (`resources/app.yml`).** Bindings (resource name, then what `app.yaml` reads): `sql-warehouse` (`${var.warehouse_id}`, CAN_USE, `WAREHOUSE_ID`), `postgres` (project `bluerridge-pm` production branch and `databricks-postgres` database, CAN_CONNECT_AND_CREATE, `LAKEBASE_ENDPOINT`), `genie-space` (`${resources.genie_spaces.bluerridge_pm_copilot.id}`, CAN_RUN, `GENIE_SPACE_ID`) and `drawings-volume` (`uc_securable` VOLUME `mfg_mc_se_sa.bluerridge_landing.drawings`, READ_VOLUME). On-behalf-of scopes are `user_api_scopes: [dashboards.genie, sql]` on the app resource, not in `app.yaml` (CLI v1.20.0 schema: `resources.apps.*.user_api_scopes`, Public Preview; a workspace admin must have enabled user authorization). Task 17 only ran `bundle validate`; the first deploy is Task 18.
