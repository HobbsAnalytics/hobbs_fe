# Build and deploy guide

The whole project is one Declarative Automation Bundle: `databricks.yml` (bundle `bluerridge_pm_copilot`, target `demo`) plus `resources/`. This page gives the one deploy order, then the reference sections behind it. The [implementation plan](superpowers/plans/2026-11-06-bluerridge-pm-copilot.md) has the task-by-task detail. The final verification run of the deployed system is [`evidence/deploy_transcript.md`](../evidence/deploy_transcript.md).

## Prerequisites

| Need | Value |
|---|---|
| Databricks CLI | v1.20.0 or newer (the version this repo was validated with) |
| Workspace | `https://fevm-mfg-mc-se-sa.cloud.databricks.com` |
| CLI profile | any profile for that workspace; the commands below use `DEFAULT` and always pass `--profile` |
| Catalog | `mfg_mc_se_sa`, which already exists (`CREATE CATALOG` is blocked in this workspace) |
| SQL warehouse | `hobbs`, id `527214d7319cb124`, serverless |
| Local tools | Python 3.10+ (`pip install -e ".[dev]"` for the unit tests), Node.js 18+ (frontend build), `uv` (renders the evidence HTML and runs the grants script) |

The bundle variables default to these values: `catalog` = `mfg_mc_se_sa`, `schema_prefix` = `bluerridge`, `warehouse_id` = `527214d7319cb124`.

Catalog `mfg_mc_se_sa` is shared with other teams: touch only objects whose schema starts with `bluerridge_`.

## Deploy order

This is the only deploy order. Each step reads what the earlier steps wrote. CLI v1.20's top-level `scripts:` are named on-demand scripts, not pre-deploy or post-deploy hooks (see Gotchas). So the steps that are not bundle resources (the schema notebook, the notebook runs and the service principal's grants) are explicit commands here, not lifecycle hooks. "Recipe" means the one-time serverless notebook run described in [Running a notebook so its outputs are real](#running-a-notebook-so-its-outputs-are-real). That is how every committed notebook output was produced.

| # | Step | Command or notebook | Result | AI cost |
|---|---|---|---|---|
| 1 | Validate | `databricks bundle validate --profile DEFAULT` | "Validation OK!" | none |
| 2 | Unity Catalog objects | `00_setup/00_create_schemas_and_volumes.ipynb` (recipe) | Seven `bluerridge_*` schemas; Volumes `bluerridge_landing.drawings` and `bluerridge_landing.project` | none |
| 3 | First bundle deploy | `databricks bundle deploy -t demo --profile DEFAULT` (on a clean workspace, see the note below the table) | The three jobs and the two pipelines | none |
| 4 | Synthetic data | `databricks bundle run job_synthetic_data -t demo --profile DEFAULT`. The committed outputs came from running its two notebooks with the recipe | 6 project CSVs and 1,200 drawing PDFs in the Volumes; the ground truth in `01_synthetic_data/outputs/` | none |
| 5 | Lakeflow ingestion | `databricks bundle run pipeline_project -t demo --profile DEFAULT`, then `databricks bundle run pipeline_drawings -t demo --profile DEFAULT` | 6 bronze streaming tables + 6 silver materialized views; `raw_files` + `drawings_raw_tracking` | none |
| 6 | Document intelligence | `03_doc_intelligence/01_parse_drawings`, `02_extract_classify`, `03_compliance_check`, `03b_compliance_guardrails`, then `04_ground_truth_scoring` (recipe, each with `disable_auto_optimization: true`). `bundle run job_doc_intelligence` runs the first four as one job | `drawings_parsed`, `drawings_extracted`, `compliance_judge_raw`, `compliance_findings`, `compliance_suppressed`, `compliance_eval`, MLflow eval runs | **Bills:** about 1,370 parsed pages plus about 3,600 extract, classify and judge calls. 03b and 04 make none |
| 7 | Code excerpts | `04_vector_search/01_load_code_excerpts` (recipe) | `bluerridge_agents.code_excerpts`, 52 rows, Change Data Feed on (the index needs it) | none |
| 8 | Gold | `05_gold/01_kpi_daily`, `02_risk_forecast`, `03_daily_brief` (recipe) | `kpi_daily`, `risk_series`, `risk_forecast`, `schedule_overdue`, `daily_brief`; MLflow forecast run | `ai_forecast` on the warehouse; 1 or 2 `ai_query` calls for the brief |
| 9 | Governance | `06_governance/apply.ipynb` (recipe) | Tags, `drawing_register` with its row filter, `grant_listing.md`, `lineage_edges.md` | none |
| 10 | Build the SPA | `cd 09_app/frontend && npm ci && npm run build` | `09_app/frontend/dist`, which is git-ignored and uploaded through `sync.include` | none |
| 11 | Full bundle deploy | `databricks bundle deploy -t demo --profile DEFAULT` | Adds the Vector Search endpoint and index, the Genie space, the Lakebase project and its five synced tables, and the app. A new app is created STOPPED | none |
| 12 | Vector Search | `04_vector_search/02_create_endpoint_and_index` (recipe) | Index synced (52 of 52), smoke test 5 of 5 | embeddings only |
| 13 | Genie | `07_genie_agent/01_create_space` (idempotent re-apply, writes `space_id.txt`), then `02_run_sample_qa` (recipe) | Space definition confirmed; `evidence/genie_qa_transcript.md` | 15 Genie questions |
| 14 | Lakebase | `08_lakebase/01_create_instance` (recipe) | Synced tables online, Postgres counts equal UC counts, latency table | none |
| 15 | Start the app | `databricks bundle run pm_copilot_app -t demo --profile DEFAULT` | Compute started, source deployed, URL printed | none |
| 16 | Service principal grants | `scripts/post_deploy_grants.sh --profile DEFAULT --out 09_app/outputs/post_deploy_grants_run.md --append` | UC grants, the row-filter mapping row, Postgres SELECT on the five tables ([details](#post-deploy-grants)) | none |
| 16b | Restart the app | `databricks apps stop bluerridge-pm-copilot --profile DEFAULT`, then `databricks bundle run pm_copilot_app -t demo --profile DEFAULT` | On a fresh app the boot self-test runs before step 16's grants, so its first run fails on missing grants. Restart after the grants, and do not expect `selftest done ok=True` until you have | none |
| 17 | Verify | `databricks apps get bluerridge-pm-copilot --profile DEFAULT -o json` (RUNNING, `user_api_scopes` intact); `databricks apps logs bluerridge-pm-copilot --profile DEFAULT --tail-lines 60 --follow --timeout 20s` (ends `selftest done ok=True`); open the app URL signed in | | one Genie question as the SP (self-test) |

**On a clean workspace (steps 3 and 11).** Four resource files read tables that steps 4 to 9 create: `resources/vector-search.yml` (the index needs `code_excerpts`), `genie-space.yml` (its 11 tables), `lakebase.yml` (the five gold tables) and `app.yml` (it binds the Genie space and Lakebase). Leave these four out of `include:` in `databricks.yml` for the first deploy (step 3), and put them back for step 11. This build added the resource files task by task in exactly this order (Tasks 4 to 18), so each deploy had its inputs. A from-scratch run of the whole sequence in one sitting was not repeated. On this workspace everything exists already, so every `bundle deploy` is the full one.

**After a code change (the short loop).** Steps 1, 10, 11, 15 and 17. Re-run step 16 if the app was recreated (a recreated app gets a new service principal) or a Lakebase re-sync recreated a table. It is idempotent, so running it anyway does no harm.

**Refreshing data.** After a gold refresh (step 8), re-sync the five synced tables (see [Lakebase + app](#lakebase--app), "Refresh") and re-run step 16.

## Costs and teardown

What keeps billing after the demo, and how to stop it. All of these commands touch only this project's resources.

| Resource | What it costs while idle | Stop it | Delete it |
|---|---|---|---|
| Lakebase project `bluerridge-pm` | The endpoint is pinned at 1 CU, and its scale-to-zero suspend timeout is **86,400 s (24 h)**. An idle project keeps one CU running for up to a day after the last connection. The app's pool keeps it awake while the app runs | Suspend sooner: `databricks postgres update-endpoint projects/bluerridge-pm/branches/production/endpoints/primary spec.suspend_timeout_duration --json '{"spec":{"suspend_timeout_duration":"300s"}}' --profile DEFAULT` (wakes in about a second). Or switch it off: `... spec.disabled --json '{"spec":{"disabled":true}}'` (re-enable with `false`) | Synced tables first, then the project (permanent, data included): `databricks postgres delete-synced-table synced_tables/mfg_mc_se_sa.bluerridge_app.<t>_synced --profile DEFAULT` for each of the five, then `databricks postgres delete-project projects/bluerridge-pm --profile DEFAULT` |
| Vector Search endpoint `bluerridge_vs` (STANDARD) | An online endpoint bills for as long as it exists, used or not | No pause. Delete it when the demo is over | `databricks vector-search-indexes delete-index mfg_mc_se_sa.bluerridge_agents.code_excerpts_vs --profile DEFAULT`, then `databricks vector-search-endpoints delete-endpoint bluerridge_vs --profile DEFAULT` |
| App `bluerridge-pm-copilot` | App compute bills while it is running | `databricks apps stop bluerridge-pm-copilot --profile DEFAULT` (start again with `bundle run pm_copilot_app`) | `databricks apps delete bluerridge-pm-copilot --profile DEFAULT` (its service principal goes with it) |
| Jobs `bluerridge-doc-intelligence`, `bluerridge-risk-forecast`, `bluerridge-synthetic-data` | Nothing: they never run unattended. The risk job's weekly schedule is **PAUSED**; the other two have no schedule | Already idle | Removed by `bundle destroy` |
| Pipelines `bluerridge-pipeline-project`, `bluerridge-pipeline-drawings` | Nothing: triggered, serverless, they run only when started | Already idle | Removed by `bundle destroy` |
| SQL warehouse `hobbs` | Shared, not created by this bundle; it stops on its own auto-stop | Not ours to change | Not ours to delete |

> **Do not run `databricks bundle run job_doc_intelligence` to "check it works".** It re-bills the three AI steps (about 1,370 parsed pages plus about 3,600 extract, classify and judge calls). It also replaces `drawings_parsed`, `drawings_extracted`, `compliance_findings` and `compliance_suppressed` with fresh, slightly different model output, which would drift from the committed evidence. The committed outputs came from one-time runs; the job is there to show the production shape.

**Everything at once.** `databricks bundle destroy -t demo --profile DEFAULT` removes every bundle resource: the app, the jobs, the pipelines and their tables, the Vector Search endpoint and index, the Genie space, the Lakebase project and its synced tables. The schemas, Volumes and the tables written by notebooks are not bundle resources. Drop them with `DROP SCHEMA mfg_mc_se_sa.bluerridge_<name> CASCADE` for each of the seven `bluerridge_*` schemas, and never for any other schema in the shared catalog. If you delete the Lakebase project outside the bundle, also remove `resources/lakebase.yml` from `databricks.yml` before the next `bundle deploy`, otherwise the deploy recreates it. Only `bluerridge-pm` belongs to this project; other Lakebase projects in the workspace are not ours.

## Running a notebook so its outputs are real

Committed notebooks are executed on the workspace as a one-time serverless job run. [`scripts/nb_evidence.py`](../scripts/nb_evidence.py) (standard library only) then writes the run's own cell outputs into the `.ipynb`, so what a reader sees in the notebook is what the run produced. The commands below use `01_synthetic_data/01_generate_project_data.ipynb` as the worked example. For another notebook, change `NB`. Every line can be copied and pasted as is into bash or zsh from the repo root.

```bash
NB=01_synthetic_data/01_generate_project_data      # the notebook, without ".ipynb"
ME=$(databricks current-user me --profile DEFAULT -o json | python3 -c 'import json,sys; print(json.load(sys.stdin)["userName"])')
SCRATCH="/Workspace/Users/$ME/_scratch_bluerridge"  # throwaway workspace folder

# 1. Put the notebook in the scratch folder (import does not create parent folders)
databricks workspace mkdirs "$SCRATCH/$(dirname $NB)" --profile DEFAULT
databricks workspace import "$SCRATCH/$NB" --file "$NB.ipynb" --format JUPYTER --overwrite --profile DEFAULT

# 2. Run it once. A notebook_task with no cluster spec runs on serverless compute, and `jobs submit` waits for the
#    run to finish. disable_auto_optimization stops serverless from retrying a failed run (a retry repeats any AI calls).
cat > submit.json <<EOF
{"run_name": "evidence: $NB", "tasks": [{"task_key": "main", "disable_auto_optimization": true,
  "notebook_task": {"notebook_path": "$SCRATCH/$NB"}}]}
EOF
databricks jobs submit --json @submit.json --profile DEFAULT -o json > result.json

# 3. Export the run's record of the executed notebook, using the TASK run id (.tasks[0].run_id)
read -r RUN TASK URL < <(python3 -c "import json; d=json.load(open('result.json')); print(d['run_id'], d['tasks'][0]['run_id'], d['run_page_url'])")
databricks jobs export-run $TASK --views-to-export ALL --profile DEFAULT -o json > export.json

# 4. Write that run's real outputs, run id and run URL into the notebook
python3 -I scripts/nb_evidence.py export.json "$NB.ipynb" --run-id $RUN --task-run-id $TASK --run-url "$URL"

# 5. Render a readable HTML page for the evidence folder. uv fetches nbconvert on the fly (a system
#    python3 refuses `pip install` under PEP 668); in a virtualenv with nbconvert, drop the "uv run" prefix.
uv run --no-project --with nbconvert python -m nbconvert --to html "$NB.ipynb" --output-dir evidence/notebook_html_exports

# 6. Pull back every file the notebook wrote to outputs/, and drop the exec bit the export adds
OUT="$(dirname $NB)/outputs"
for f in $(databricks workspace list "$SCRATCH/$OUT" --profile DEFAULT -o json | python3 -c 'import json,sys; [print(o["path"].rsplit("/",1)[1]) for o in json.load(sys.stdin) if o.get("object_type")=="FILE"]'); do
  databricks workspace export "$SCRATCH/$OUT/$f" --file "$OUT/$f" --format AUTO --profile DEFAULT
done
chmod 644 "$OUT"/*

# 7. Remove the scratch folder (the run itself stays exportable)
databricks workspace delete "$SCRATCH" --recursive --profile DEFAULT
```

Things the recipe depends on:

- **Why step 4 exists.** The HTML that `jobs export-run` returns carries the executed notebook as a base64 blob, so its printed text and tables cannot be read as text. `nb_evidence.py` decodes the blob and writes the outputs into the `.ipynb` as plain JSON. The HTML to commit is the one `nbconvert` renders from that enriched notebook in step 5, not the raw run page (`nb_evidence.py --html` can still save the raw page).
- **The notebook must not change between steps 1 and 4.** The tool compares every code cell's source with the run's and stops on a mismatch. Markdown cells are only checked to be markdown, so an edit to prose goes unnoticed. After any code edit, re-import and re-run. A prose-only edit after the run (Task 24 added one disclosure line to `05_gold/03_daily_brief.ipynb`) can be checked by exporting the run again and re-running step 4 on a copy: the result must equal the committed file byte for byte.
- **Supported outputs** are stdout (`print`) and `display(df)` tables. Any other output type (images, HTML, errors) makes the tool stop rather than drop it silently.
- **`outputs/` is relative.** A notebook run uses its own folder as the working directory, so `outputs/...` lands next to the workspace notebook. The scratch folder has no `outputs/` directory, so the notebooks create it themselves.
- **A notebook that imports a module from its own folder** (`02_generate_drawings.ipynb` imports `02_generate_drawings.py`) needs that file next to it in step 1: `databricks workspace import "$SCRATCH/$NB.py" --file "$NB.py" --format AUTO --overwrite --profile DEFAULT`. A `.py` without the `# Databricks notebook source` header lands as a workspace file (`workspace list` shows `FILE`), and the notebook puts its working directory on `sys.path`. A bundle deploy uploads the module the same way.
- **Extra inputs.** Some notebooks read a sibling file (for example the Genie definition, the excerpt corpus or `compliance_lib.py`). Their submit payloads are committed under each folder's `outputs/submit_payloads/`.

## Lakebase + app

**Flavor and how it is declared.** The "instance" `bluerridge-pm` is a Lakebase **Autoscaling** project (one `production` branch, one `primary` read-write endpoint, Postgres 17), not a Provisioned `database_instances` instance. Two pieces of evidence support the choice:

- `databricks bundle schema` on CLI v1.20.0 defines `postgres_projects`, `postgres_branches`, `postgres_endpoints`, `postgres_databases`, `postgres_catalogs` and `postgres_synced_tables`, as well as the older `database_instances` and `synced_database_tables`.
- Current Lakebase guidance treats Provisioned as retired and says the legacy `synced_database_tables` resource fails on current Lakebase. A Databricks App binds Lakebase through the `postgres` resource key (`branch` + `database`), which targets Autoscaling projects. The old `database` key (`instance_name`) is deprecated.

The project and the five synced tables deploy as ordinary bundle resources from `resources/lakebase.yml`. No SDK-only path is needed, and no YAML is dead. `01_create_instance.ipynb` only confirms their state.

**Capacity.** The Autoscaling floor is 0.5 CU. The project pins the endpoint to 1 CU min and max (`default_endpoint_settings`), the closest match to the plan's "CU_1". The Postgres database is `databricks_postgres`, and the synced tables create the schema `bluerridge_app`. The endpoint host and counts are in `08_lakebase/outputs/synced_tables_listing.md`. For cost, see [Costs and teardown](#costs-and-teardown).

**Synced tables (SNAPSHOT).** Each source `mfg_mc_se_sa.bluerridge_gold_pm.<t>` becomes the UC table `mfg_mc_se_sa.bluerridge_app.<t>_synced` and the Postgres table `bluerridge_app.<t>_synced`, for these five tables: `kpi_daily`, `compliance_findings`, `risk_forecast`, `schedule_overdue`, `daily_brief`. They are SNAPSHOT because the gold tables are rewritten with `CREATE OR REPLACE` and have no Change Data Feed, which TRIGGERED and CONTINUOUS need. Each synced table has its own small managed pipeline in `mfg_mc_se_sa.bluerridge_app`.

**Refresh.** After any gold refresh, re-sync each table by starting an update of its pipeline: `databricks postgres get-synced-table synced_tables/mfg_mc_se_sa.bluerridge_app.<t>_synced --profile DEFAULT` shows `status.pipeline_id`, then run `databricks pipelines start-update <pipeline_id> --profile DEFAULT`. Re-run `scripts/post_deploy_grants.sh` if a table was recreated.

**`drawing_register` is never synced.** It has a Unity Catalog row filter, and the filter does not propagate to a Postgres copy. The app reads that table through the SQL warehouse.

**App resource binding (`resources/app.yml`).**

```yaml
resources:
  - name: postgres                      # the resource key; app.yaml reads it with `valueFrom: postgres`
    postgres:
      branch: ${resources.postgres_projects.bluerridge_pm.name}/branches/production
      database: ${resources.postgres_projects.bluerridge_pm.name}/branches/production/databases/databricks-postgres
      permission: CAN_CONNECT_AND_CREATE
```

The app connects to Lakebase as its service principal, so `postgres` is not in its `user_api_scopes`.

**How the app gets credentials.** The platform injects `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER` (the app service principal's client id) and `PGSSLMODE`. The entry `env: - name: LAKEBASE_ENDPOINT / valueFrom: postgres` adds the endpoint path `projects/bluerridge-pm/branches/production/endpoints/primary`. There is no static password. Each new pooled connection works like this:

- The backend calls `WorkspaceClient().postgres.generate_database_credential(endpoint=...)`, which returns an OAuth token valid for about an hour.
- It passes that token as the psycopg `password`, with `sslmode=require`.
- The pool's `max_lifetime` of 1,800 s retires connections before the token expires (`09_app/backend/lakebase.py`).

Queries use schema-qualified names such as `bluerridge_app.kpi_daily_synced`.

**Grants (the first-boot `42501`).** Binding the database lets the SP connect and create its own objects, but not read the schema `bluerridge_app`, which the sync writer owns. Until the grants run, a Lakebase query from the SP fails with `psycopg.errors.InsufficientPrivilege` (SQLSTATE `42501`). `scripts/post_deploy_grants.sh` (step 16) fixes this and also handles the role. The manual equivalent, for reference:

1. Get the SP's application id: `databricks apps get bluerridge-pm-copilot --profile DEFAULT -o json`, field `service_principal_client_id`.
2. Check `databricks postgres list-roles projects/bluerridge-pm/branches/production --profile DEFAULT`. Binding the `postgres` resource makes the platform create the role itself: the role id is `dbrx-apps-<client id>`, and the Postgres role name is the bare client id. Only if it is missing, create one (the command is in the header of `08_lakebase/app_grants.sql`).
3. Run `08_lakebase/app_grants.sql` as the project owner. Replace every `${APP_SP_ROLE}` with the **bare** application id, such as `02a6516a-0d8f-...`, and add no quotes of your own: the file already wraps the placeholder in double quotes, which Postgres needs because the id contains hyphens. A value you quoted yourself would become `""<id>""` and fail, and the script refuses one. Connect with psql or psycopg to the endpoint host, database `databricks_postgres`, as your own user, with a credential from `databricks postgres generate-database-credential projects/bluerridge-pm/branches/production/endpoints/primary --profile DEFAULT -o json`.

The file grants CONNECT on the database, USAGE on the schema and SELECT on the five tables. It does **not** use `ALTER DEFAULT PRIVILEGES`, because the owner cannot set it for the sync writer role. Re-run the file if a re-sync recreates a table. The grants apply to new connections and queries without an app restart. They were dry-run in a rolled-back transaction in Task 16 and applied for real in Task 18. Every run is recorded in `09_app/outputs/post_deploy_grants_run.md`.

## Genie space

- **Space id:** `01f1db9edffa1a298195db2806ce45e3`, committed in `07_genie_agent/outputs/space_id.txt` (an id is not a secret). Its title is "Blue Ridge LNG — PM Co-Pilot (synthetic)" and its warehouse is `hobbs`.
- **How it is created:** `bundle schema` in CLI v1.20.0 defines `genie_spaces` (grep the output for `genie`), so `resources/genie-space.yml` declares the space, and `databricks bundle deploy -t demo --profile DEFAULT` creates it. The body comes from `07_genie_agent/genie_space.geniespace.json`, which `python3 -I 07_genie_agent/build_space.py` generates. It holds 11 curated tables with descriptions and synonyms, one general instruction block and the 10 curated example SQLs. The same script runs every verified SQL on the warehouse and writes `sample_questions.md`, `heldout_questions.md` and `benchmark_expected.json`, so the expected answers are query results, not typed numbers. Create the folder named by `parent_path` first: `databricks workspace mkdirs "/Workspace/Users/$ME/genie_spaces" --profile DEFAULT`.
- **Idempotent re-apply:** `07_genie_agent/01_create_space.ipynb` pages through the workspace's Genie spaces and finds this exact title. It `PATCH`es the same definition, or `POST`s a new space if the bundle has not been deployed. It asserts that the five held-out questions are not in the space, writes `space_id.txt`, and never touches another space. When running it with the recipe, upload the definition next to the notebook as `genie_space.json` (the workspace refuses to import a file ending in `.geniespace.json`), plus `benchmark_expected.json`.
- **Benchmark:** `02_run_sample_qa.ipynb` asks 15 questions (10 curated, 5 held-out) as fresh conversations through the Genie Conversation API and writes `evidence/genie_qa_transcript.md`. It calls the REST endpoints through `WorkspaceClient.api_client`, because the serverless SDK has no `w.genie`.
- **App calls run as the signed-in PM.** The app calls the space on behalf of the user (OBO, `user_api_scopes: [dashboards.genie, sql]`). Each query therefore runs with that PM's own Unity Catalog permissions, including the `drawing_register` row filter, not as the app's service principal. The chat tries the managed Genie MCP server first and falls back to the Conversation API on a refusal that comes before execution. In the live signed-in session, MCP refused the user's token with 403 and the fallback answered (`09_app/outputs/live_obo_chat.md`).

## Vector Search: bundle resources, with one ordering rule

`bundle schema` in CLI v1.20.0 defines `vector_search_endpoints` and `vector_search_indexes` (grep the output for `vector_search`), and `bundle validate` accepts them. So `resources/vector-search.yml` declares the endpoint `bluerridge_vs` (STANDARD) and the Delta Sync index `code_excerpts_vs` as ordinary bundle resources, with no SDK-only path. The ordering rule (steps 7, 11 and 12) is: load `code_excerpts`, then deploy, then sync. Right after a deploy the endpoint reads ONLINE, but the index can stay "pending endpoint provisioning" for several minutes. To validate the excerpt files locally, run `uv run --no-project --with pytest --with pyyaml python -m pytest 04_vector_search/tests`.

## Governance notes

- **App service principal:** step 16 runs the `{app_sp}` statements of `06_governance/grants.sql`:
  - USE CATALOG on `mfg_mc_se_sa`.
  - USE SCHEMA and SELECT on `bluerridge_gold_pm` and `bluerridge_agents`.
  - USE SCHEMA on `bluerridge_landing`, and READ VOLUME on `bluerridge_landing.drawings`.
  - A MERGE of `('<app sp application id>', '*')` into `discipline_access`, the row-filter mapping. Without that row the app sees 0 rows of `drawing_register`.
- **Re-running `06_governance/apply.ipynb` now:** the app's service principal exists and holds direct grants (step 16), so a fresh run's `SHOW GRANTS` lists the SP's grants on `bluerridge_gold_pm`, `bluerridge_agents` and `bluerridge_landing`. The SP's `'*'` row also shows in the mapping table. The committed `evidence/grant_listing.md` predates the app. Its sentence "No direct grants were made by this task" refers to Task 14's own changes, not the SP's later grants, and its "TODO for Task 24" was done by the grants script.
- **Groups:** Unity Catalog grants reject workspace-local groups (`PRINCIPAL_DOES_NOT_EXIST`), so none exist. If an account admin supplies `bluerridge-pm` / `bluerridge-engineers`, run `06_governance/apply.ipynb` with the widgets `pm_group` / `engineer_group`. To remove them later, `REVOKE` the same privileges, then ask the account admin to delete the groups.
- **Tags:** the account's governed tags own the keys `layer`, `sensitivity`, `data_class` and `domain`. The project uses `br_layer`, `br_sensitivity`, `br_data_class`, `br_domain` and `synthetic`.
- **Filters:** never attach a row filter or mask to `kpi_daily`, `compliance_findings`, `risk_forecast` or a pipeline input, because the Lakebase sync and the notebooks would break. Only `drawing_register` carries one.

## Gotchas found while building

- `databricks workspace export` writes files with the exec bit (mode 755). `chmod 644` anything under `outputs/` before `git add`.
- `SHOW SCHEMAS ... LIKE` uses `*` as its wildcard and matches `%` literally, so `LIKE 'bluerridge_%'` returns nothing. Use `LIKE 'bluerridge_*'`.
- Auto Loader's `binaryFile` format has a fixed schema. It rejects `cloudFiles.schemaEvolutionMode=rescue` (`CF_UNSUPPORTED_SCHEMA_EVOLUTION_MODE`; use `none`) and adds no `_rescued_data` column, so a malformed file is an ordinary row. `pipeline_drawings.py` sets `_rescued_data` itself for files without the `%PDF-` header. A streaming table also keeps the row of a source file that is later deleted; only a full refresh removes it.
- A failed serverless notebook task is retried automatically (`attempt_number` 1 in `databricks jobs get-run`), and the retry runs the whole notebook again, AI calls included. For a notebook that calls an AI function, put `"disable_auto_optimization": true` on the task in the `jobs submit` JSON. For example, `03_doc_intelligence/01_parse_drawings.ipynb` bills about 1,370 pages per run. The bundle schema has the same field for job tasks. `jobs submit` also stops waiting after 20 minutes (`--timeout`). For a longer notebook, use `--no-wait` and poll `databricks jobs get-run`.
- `databricks bundle validate` accepts any key under `experimental.scripts`, so a passing validate does not prove a lifecycle hook name is real. The top-level `scripts:` block holds named scripts that run on demand with `databricks bundle run <name>`. That is why the deploy order has no hooks.
- `databricks bundle summary` prints `URL: (not deployed)` for the app even while it is RUNNING. `databricks apps get` is the authoritative state.

## App build and deploy

**Layout.** `09_app/` is the app's `source_code_path`. It holds `app.yaml` (uvicorn `backend.main:app` on port 8000), `requirements.txt`, `backend/` (FastAPI) and `frontend/` (React 18 + Vite + TS + Tailwind). Vite builds to `09_app/frontend/dist`, and FastAPI serves it: static assets plus an `index.html` fallback for client routes. `/health` and `/api/*` keep priority, and an unknown `/api/*` path returns a 404, not the SPA.

**Order.** Use steps 10, 11, 15, 16 and 17 of the [deploy order](#deploy-order). A bare `bundle deploy` of a new app leaves it STOPPED with no deployment ("Start the app compute to deploy the app."), and `bundle run pm_copilot_app` starts it. The first deploy, from Task 18, is recorded in `09_app/outputs/first_deploy.md`. `databricks apps logs` without `--follow` keeps the connection open after printing; `--follow --timeout 20s` returns.

**Why `sync.include`.** `bundle deploy` skips git-ignored files, so `databricks.yml` has `sync.include: [09_app/frontend/dist/**]`. When the build exists, `databricks bundle sync --dry-run` lists `09_app/frontend/dist/index.html` and `dist/assets/*` for upload, and nothing under `node_modules`. If `dist/` is missing, the deployed app still answers `/health`, but `/` returns 404 "Frontend build not found".

**Local dev.** For the API on :8000, run `cd 09_app && pip install -r requirements.txt && uvicorn backend.main:app --reload`. For Vite on :3000, which proxies `/api` to :8000, run `cd 09_app/frontend && npm run dev`. Tests: `pytest 09_app/backend/tests -q` (in Task 24: `uv run --no-project --with-requirements requirements.txt --with pytest --with httpx python -m pytest backend/tests -q` from `09_app`, 201 passed) and `cd 09_app/frontend && npx vitest run` (43 passed).

**App resource (`resources/app.yml`).** Each binding gives a resource name, the permission and what `app.yaml` reads:

- `sql-warehouse`: `${var.warehouse_id}`, CAN_USE, read as `WAREHOUSE_ID`.
- `postgres`: the project `bluerridge-pm` production branch and its `databricks-postgres` database, CAN_CONNECT_AND_CREATE, read as `LAKEBASE_ENDPOINT`.
- `genie-space`: `${resources.genie_spaces.bluerridge_pm_copilot.id}`, CAN_RUN, read as `GENIE_SPACE_ID`.
- `drawings-volume`: the `uc_securable` VOLUME `mfg_mc_se_sa.bluerridge_landing.drawings`, READ_VOLUME.

The on-behalf-of scopes are `user_api_scopes: [dashboards.genie, sql]` on the app resource, not in `app.yaml`. The CLI v1.20.0 schema has `resources.apps.*.user_api_scopes`, user authorization is enabled in this workspace, and the deploy accepted the scopes. The `${resources...}` references resolved at the first deploy.

## Auth: how OBO is wired

Research memo with sources: [`09_app/backend/AUTH_NOTES.md`](../09_app/backend/AUTH_NOTES.md). It cites the Databricks Apps auth and HTTP-headers docs, `databricks/app-templates` and `databricks-solutions/databricks-apps-cookbook`.

- **Two identities.** The Genie chat runs **on behalf of the signed-in PM** (OBO). Everything else runs as the **app service principal**: warehouse reads, Lakebase, Volume PDFs and Vector Search.
- **Headers.** On every request the Apps proxy forwards `x-forwarded-access-token`, `x-forwarded-email`, `x-forwarded-user` and `x-forwarded-preferred-username`. The token is the user's short-lived token, present only when `user_api_scopes` are set. None of these headers exist in local dev.
- **Code.** All of it is in `backend/auth.py`:
  - `get_user_token(request)` reads the forwarded token.
  - `user_workspace_client(request)` builds `WorkspaceClient(token=<forwarded token>, auth_type="pat")` per request. A missing header gives a 401: the client fails closed and never falls back to the SP. `auth_type="pat"` is required because the app's environment also holds the SP's `DATABRICKS_CLIENT_ID` and secret.
  - `sp_workspace_client()` is a cached `WorkspaceClient()` (SP OAuth from the injected env).
  - `identity(request)` reads headers only.
- **`GET /api/whoami`** returns `{email, user_name, auth_mode}`. `auth_mode` is `OBO` when a user token was forwarded, else `SP`. `user_name` is the preferred username, else `x-forwarded-user`. The route logs `email` and `auth_mode` (logger `bluerridge.auth`, stdout) and never returns or logs the token; this is tested with a planted token.
- **Scopes.** `dashboards.genie` is the platform's alias of `genie`, and `sql` is also granted. After any change to `user_api_scopes`, do all of the following, because a deploy that adds a resource can drop scopes and users must re-consent:
  1. Redeploy.
  2. Restart the app.
  3. Re-check `databricks apps get ... -o json`.
  4. Reload in a fresh browser session.
- **Live check (done in Task 24).** The user opened the app in their own managed Chrome profile. A browser that is not a managed profile is stopped by Okta's device check (Task 18). The log shows `whoami email=<user> auth_mode=OBO` and one chat with `outcome=done got_sql=True rows=85` (`09_app/outputs/live_obo_chat.md`). An unauthenticated `/api/*` call gets a 401 `{}` from the proxy.

## Post-deploy grants

`scripts/post_deploy_grants.sh --profile DEFAULT [--out FILE [--append]]` gives the app's service principal what it needs. Run it after every `bundle deploy` that creates or recreates the app, because a recreated app gets a new SP. The script is idempotent (GRANTs are no-ops when already held, and the mapping row is a MERGE). It runs as you and never prints a credential. Its steps:

1. **(a)** Reads `service_principal_client_id` (the application id) and `service_principal_name` from `databricks apps get bluerridge-pm-copilot`.
2. **(b)** Runs the `{app_sp}` statements of `06_governance/grants.sql` on the `hobbs` warehouse: USE CATALOG `mfg_mc_se_sa`; USE SCHEMA + SELECT on `bluerridge_gold_pm` and `bluerridge_agents`; USE SCHEMA `bluerridge_landing` + READ VOLUME `bluerridge_landing.drawings`.
3. **(c)** Runs the same file's MERGE of `('<application id>', '*')` into `bluerridge_agents.discipline_access`. In the app's SQL, `current_user()` returns the SP's UUID, its application id (the docs say it "returns the UUID of the service principal"). That is the value the `drawing_register` row filter matches.
4. **(d)** Finds the SP's Lakebase role with `list-roles` (`postgres_role` = the application id) and creates it with `create-role` only if it is missing. It then applies `08_lakebase/app_grants.sql` through psycopg as the project owner, with a database credential generated in-process (SDK `w.postgres.generate_database_credential`) and never echoed.
5. **Verify.** Runs `SHOW GRANTS \`<sp>\` ON ...` for each securable, checks the mapping row, `has_database_privilege` and `has_schema_privilege`, and prints a `\dp`-style listing of `bluerridge_app.*` (SELECT, no INSERT).

The script needs `uv`, because the Python step runs as `uv run --with databricks-sdk --with psycopg[binary]`. Alternatively, set `PYTHON=<interpreter with both>`. All three runs so far are in `09_app/outputs/post_deploy_grants_run.md`: the first apply and an idempotent re-run (Task 18), and the Task 24 re-run.

## npm audit

`npm audit` in `09_app/frontend` (Task 24) reports 4 findings, all in two direct dependencies. Each one can only be fixed by a major-version upgrade:

| Package | Severity | Advisory | Exposure here |
|---|---|---|---|
| `vite` (≤ 6.4.3) and its `esbuild` (≤ 0.24.2) | high / moderate | The esbuild **dev server** answers cross-origin requests (GHSA-67mh-4wv8-2f99) | Dev only. The deployed app serves the static `dist/` build from FastAPI; no Vite or esbuild server runs in production |
| `react-router-dom` / `react-router` (6.0.0 to 7.17.0) | moderate | Open redirect via a backslash in `<Link>`/`useNavigate` (GHSA-wrjc-x8rr-h8h6); constructor injection in SSR hydration (GHSA-337j-9hxr-rhxg) | The app does no SSR. Its links and navigations are fixed in-app paths and drawing ids from the API, not user-supplied URLs |

`npm audit --omit=dev` (production dependencies only) reports 2 moderate (react-router) and 0 high. The fixes (`vite@8`, `react-router-dom@7`) are breaking upgrades and were left alone for the demo. Do them before any production use.
