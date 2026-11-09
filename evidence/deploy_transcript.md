# Final deploy verification (Task 24)

Run on 2026-11-08 between 20:50 and 21:05 US Central (2026-11-09 02:50 to 03:05 UTC), from commit `19076c9` on `main`, as `joseph.hobbs@databricks.com`, CLI v1.20.0, profile `DEFAULT`. Every command and its outcome is below. No token was minted, passed or printed. Grant credentials are generated inside the grants script and never echoed. No AI job was run. `bluerridge-doc-intelligence` would re-bill about 1,370 parsed pages plus about 3,600 extract, classify and judge calls.

**Why there was no redeploy.** The app's active deployment `01f1dbe7fb1c1b8a8ae3438d566edf44` was created at 2026-11-09T02:48:02Z, after HEAD `19076c9` was committed (02:47:16Z). No app code changed after that: `git diff HEAD` touches no file under `09_app/backend` (other than the `AUTH_NOTES.md` memo), `09_app/frontend/src`, `app.yaml`, `requirements.txt`, `resources/` or `databricks.yml`. A fresh local `npm run build` (step 7) produced the same asset hashes that the live app served in the signed-in session (`index-JMtDCmtL.js`, `index-Cq4R4OKp.css`, `DrawingPage-Biw1XFLZ.js`, `pdf.worker.min-GB3t0DcA.mjs`; see [`live_obo_chat.md`](../09_app/outputs/live_obo_chat.md)). So the deployed SPA is the HEAD build.

**Deploy model.** CLI v1.20's top-level `scripts:` are named on-demand scripts, not pre-deploy or post-deploy hooks (confirmed in Task 1; see `docs/BUILD.md`, Gotchas). The deploy is therefore the documented sequence in [`docs/BUILD.md`](../docs/BUILD.md#deploy-order): `bundle deploy` for every bundle resource, then `bundle run pm_copilot_app`, then `scripts/post_deploy_grants.sh`. This transcript re-verifies the deployed state rather than redeploying it.

## 1. `databricks bundle validate --profile DEFAULT`

```
Name: bluerridge_pm_copilot
Target: demo
Workspace:
  Host: https://fevm-mfg-mc-se-sa.cloud.databricks.com
  User: joseph.hobbs@databricks.com
  Path: /Workspace/Users/joseph.hobbs@databricks.com/.bundle/bluerridge_pm_copilot/demo

Validation OK!
```

Exit code 0.

## 2. `databricks bundle summary --profile DEFAULT` (what the bundle has deployed)

| Kind | Bundle key | Deployed as |
|---|---|---|
| App | `pm_copilot_app` | `bluerridge-pm-copilot` (the summary prints `URL: (not deployed)` for it; `apps get` in step 4 is authoritative: RUNNING with an active deployment) |
| Genie space | `bluerridge_pm_copilot` | "Blue Ridge LNG — PM Co-Pilot (synthetic)", `01f1db9edffa1a298195db2806ce45e3` |
| Jobs | `job_doc_intelligence`, `job_risk_forecast`, `job_synthetic_data` | ids `1046999724912456`, `563080592506156`, `461121196221318` |
| Pipelines | `pipeline_project`, `pipeline_drawings` | `1d76045d-1abc-47f3-8336-f3bc6eb8d077`, `6201f0e1-ccb9-4768-bba8-adf2473245cd` |
| Postgres project | `bluerridge_pm` | "Blue Ridge PM Co-Pilot hot path" (`projects/bluerridge-pm`) |
| Postgres synced tables | 5 | `mfg_mc_se_sa.bluerridge_app.{kpi_daily,compliance_findings,risk_forecast,schedule_overdue,daily_brief}_synced` |
| Vector Search | `bluerridge_vs`, `code_excerpts_vs` | endpoint `bluerridge_vs`, index `mfg_mc_se_sa.bluerridge_agents.code_excerpts_vs` |

Read-only state checks of the billable resources, the same session:

| Command | Result |
|---|---|
| `databricks jobs get <id>` + `jobs list-runs --job-id <id>` for the three jobs | `bluerridge-doc-intelligence`: no schedule, 0 runs. `bluerridge-risk-forecast`: schedule **PAUSED**, 0 runs. `bluerridge-synthetic-data`: no schedule, 0 runs. (All committed evidence came from one-time `jobs submit` runs.) |
| `databricks vector-search-endpoints get-endpoint bluerridge_vs` | STANDARD, ONLINE, 1 index |
| `databricks postgres get-endpoint projects/bluerridge-pm/branches/production/endpoints/primary` | ACTIVE, 1 CU min / 1 CU max, `suspend_timeout_duration` 86400s, not disabled |

## 3. `scripts/post_deploy_grants.sh --profile DEFAULT --out 09_app/outputs/post_deploy_grants_run.md --append`

Exit code 0. The script appended a third run, "Run 2026-11-09 02:53:58 UTC", to [`09_app/outputs/post_deploy_grants_run.md`](../09_app/outputs/post_deploy_grants_run.md). It is idempotent:

| Step | Result |
|---|---|
| (a) app SP | application id `02a6516a-0d8f-49e9-8965-56e89fa12ad4`, display name `app-p3l9xk bluerridge-pm-copilot`. Postgres role already present (`created by this run: no`) |
| (b) 7 Unity Catalog GRANTs (USE CATALOG; USE SCHEMA + SELECT on `bluerridge_gold_pm` and `bluerridge_agents`; USE SCHEMA `bluerridge_landing` + READ VOLUME `drawings`) | all OK; `SHOW GRANTS` lists each one for the SP |
| (c) row-filter mapping MERGE `('02a6516a-…', '*')` into `discipline_access` | OK, `num_inserted_rows=0`: the row was already there |
| (d) `08_lakebase/app_grants.sql` (CONNECT, USAGE, SELECT on the five `*_synced` tables) | 7 × GRANT; `has_database_privilege` CONNECT = True, `has_schema_privilege` USAGE = True; `\dp` shows `=r` (SELECT) for the SP on all five tables and no INSERT |
| Final line | `[grants] done.` |

The connection line reads "with a freshly generated database credential (not shown)". No credential appears in the output.

## 4. `databricks apps get bluerridge-pm-copilot --profile DEFAULT -o json` (fields)

| Field | Value |
|---|---|
| `app_status` | **RUNNING**, "App has status: App is running" |
| `compute_status` | **ACTIVE**, "App compute is running." |
| `active_deployment` | `01f1dbe7fb1c1b8a8ae3438d566edf44`, mode SNAPSHOT, **SUCCEEDED** ("App started successfully"), created 2026-11-09T02:48:02Z |
| `pending_deployment` | none |
| `url` | `https://bluerridge-pm-copilot-7474644652812129.aws.databricksapps.com` |
| `service_principal_client_id` | `02a6516a-0d8f-49e9-8965-56e89fa12ad4` |
| `user_api_scopes` | `dashboards.genie`, `sql` (survived the deploy) |
| `effective_user_api_scopes` | `dashboards.genie`, `iam.access-control:read`, `iam.current-user:read`, `sql` |
| resources | `sql-warehouse`, `postgres`, `genie-space`, `drawings-volume` |

## 5. `databricks apps logs bluerridge-pm-copilot --profile DEFAULT --tail-lines 0 --follow --timeout 25s`

The boot of deployment `01f1dbe7…` (timestamps UTC). Nothing was removed, because the self-test logs counts and ids only:

```
2026-11-09T02:48:39Z [BUILD] [INFO] Starting app with command: [uvicorn backend.main:app --host 0.0.0.0 --port 8000]
2026-11-09T02:48:40Z [APP] INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
2026-11-09T02:48:41Z [BUILD] [INFO] Deployment 01f1dbe7fb1c1b8a8ae3438d566edf44 ended in 14.79297825s
2026-11-09T02:48:41Z [BUILD] [INFO] Deployment successful
2026-11-09T02:48:41Z [APP] INFO bluerridge.selftest: selftest lakebase kpi_daily_synced rows=90
2026-11-09T02:48:41Z [APP] INFO bluerridge.selftest: selftest lakebase compliance_findings_synced rows=1379
2026-11-09T02:48:41Z [APP] INFO bluerridge.selftest: selftest lakebase risk_forecast_synced rows=64
2026-11-09T02:48:41Z [APP] INFO bluerridge.selftest: selftest lakebase schedule_overdue_synced rows=7
2026-11-09T02:48:41Z [APP] INFO bluerridge.selftest: selftest lakebase daily_brief_synced rows=1
2026-11-09T02:48:42Z [APP] INFO bluerridge.selftest: selftest warehouse current_user=02a6516a-0d8f-49e9-8965-56e89fa12ad4 drawing_register_visible=1200
2026-11-09T02:48:43Z [APP] INFO bluerridge.selftest: selftest volume BRL-PIP-ISO-0004.pdf exists=True size=6150
2026-11-09T02:48:43Z [APP] INFO bluerridge.selftest: selftest vector_search mode=vs hits=4
2026-11-09T02:48:43Z [APP] INFO bluerridge.selftest: selftest route compliance_summary reviewed=238 failed=51
2026-11-09T02:48:43Z [APP] INFO bluerridge.selftest: selftest route compliance_findings total=85 bbox_raw_type=list bbox_pg_type=jsonb bbox_type=list bbox_len=4 bbox_floats=True
2026-11-09T02:48:43Z [APP] INFO bluerridge.selftest: selftest route risk_top n=5 high=26
2026-11-09T02:48:43Z [APP] INFO bluerridge.selftest: selftest route overdue late=6 due_today=1
2026-11-09T02:48:43Z [APP] INFO bluerridge.selftest: selftest route kpi_today ok=True
2026-11-09T02:48:43Z [APP] INFO bluerridge.selftest: selftest route brief_today ok=True
2026-11-09T02:48:54Z [APP] INFO bluerridge.selftest: selftest genie transport=mcp status=COMPLETED got_sql=True rows=1 headline=51
2026-11-09T02:48:54Z [APP] INFO bluerridge.selftest: selftest done ok=True
```

All sources were reached as the SP: Lakebase (5 tables), the warehouse (UC row filter, SP mapped to `*`, 1,200 visible), the Volume, Vector Search, every data route, and Genie through the managed MCP server. The run ended `done ok=True`.

A second read with `--tail-lines 400`, after the user had used the app, shows the live signed-in session (`whoami ... auth_mode=OBO`, one chat `outcome=done got_sql=True rows=85` through the Conversation API fallback after an MCP 403, and a drawing PDF returning 200). Its scrubbed excerpt and analysis are in [`09_app/outputs/live_obo_chat.md`](../09_app/outputs/live_obo_chat.md).

## 6. The proxy fails closed without a session (`curl`, no credentials)

| Request | Status |
|---|---|
| `GET /api/whoami` | **401**, body `{}` |
| `GET /api/kpi/today` | **401**, body `{}` |
| `POST /api/chat` | **401** |
| `GET /health`, `GET /` | 302 to the workspace's OIDC authorize endpoint (sign-in) |

The `[HTTP]` access log records the same five requests with user agent `curl/8.7.1` and no user id (see `live_obo_chat.md`). None reached the app's own logger.

## 7. Tests and build (local, from the same commit)

| Command | Result |
|---|---|
| `pytest 09_app/backend/tests -q` (run in `09_app` as `uv run --no-project --with-requirements requirements.txt --with pytest --with httpx python -m pytest backend/tests -q`) | **201 passed** in 4.87 s |
| `cd 09_app/frontend && npx vitest run` | **6 files, 43 tests passed** |
| `cd 09_app/frontend && npm run build` (`tsc && vite build && node scripts/check-no-fixtures.mjs`) | built in 1.96 s. `check-no-fixtures: OK, 6 files in dist, no fixture strings or assets`. One advisory "chunks larger than 500 kB" warning (`index-JMtDCmtL.js` 503.83 kB, gzip 157.82 kB) |
| `npm audit` | 4 findings, all in two direct dependencies, all fixable only by a major upgrade: `vite` (high) / `esbuild` (moderate) affect the **dev server** only; `react-router-dom` / `react-router` (moderate) are open-redirect and SSR-hydration advisories. `npm audit --omit=dev`: 2 moderate (react-router), 0 high. Left as is, see `docs/BUILD.md`, "npm audit" |

## 8. Secret hygiene of this task's commits

`git diff` of every file committed in Task 24 was grepped for `token`, `dapi`, `eyJ`, `Bearer` and `password`. The matches are prose only: words such as "the user's token", "no token was minted" and "`x-forwarded-access-token`". There is no credential value, no `dapi…` personal access token and no `eyJ…` JWT. Docs and evidence files are mode 644.
