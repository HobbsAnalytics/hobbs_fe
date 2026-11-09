# Endpoint data-access self-test (Task 19)

The deployed app proves its service principal (SP) can reach every data source by running a background self-test at startup (`09_app/backend/selftest.py`, started from the FastAPI lifespan, non-blocking). It logs one line per source to the `bluerridge` logger: counts and identities only, never rows, tokens or credentials. A failure logs the error class and message and the app keeps running.

Read with `databricks apps logs bluerridge-pm-copilot --profile DEFAULT` after `databricks bundle deploy -t demo` and `databricks bundle run pm_copilot_app -t demo` (app state RUNNING, compute ACTIVE). Excerpt, 2026-11-08 (timestamps UTC):

```
2026-11-08T19:33:13Z [APP] INFO bluerridge.selftest: selftest lakebase kpi_daily_synced rows=90
2026-11-08T19:33:13Z [APP] INFO bluerridge.selftest: selftest lakebase compliance_findings_synced rows=1379
2026-11-08T19:33:13Z [APP] INFO bluerridge.selftest: selftest lakebase risk_forecast_synced rows=64
2026-11-08T19:33:13Z [APP] INFO bluerridge.selftest: selftest lakebase schedule_overdue_synced rows=7
2026-11-08T19:33:13Z [APP] INFO bluerridge.selftest: selftest lakebase daily_brief_synced rows=1
2026-11-08T19:33:15Z [APP] INFO bluerridge.selftest: selftest warehouse current_user=02a6516a-0d8f-49e9-8965-56e89fa12ad4 drawing_register_visible=1200
2026-11-08T19:33:15Z [APP] INFO bluerridge.selftest: selftest volume BRL-PIP-ISO-0004.pdf exists=True size=6150
2026-11-08T19:33:16Z [APP] INFO bluerridge.selftest: selftest vector_search mode=vs hits=4
[line from an earlier boot; verbatim copy not retained] selftest done ok=True
```

| Check | Result | Matches |
|---|---|---|
| Lakebase, 5 synced tables, SP role with a generated database credential | 90 / 1379 / 64 / 7 / 1 rows | the row counts in `08_lakebase/outputs/synced_tables_listing.md` |
| SQL warehouse, `drawing_register` row filter | `current_user` is the SP application id, 1200 rows visible | the existing `discipline_access` row `('02a6516a-…','*')`; no change to `post_deploy_grants.sh` was needed |
| Volume (Files API) | known PDF exists, 6150 bytes | |
| Vector Search | `mode=vs` (the index answered the exact-label filter query and the top-k related query as the SP; no SQL fallback, no extra grant) | |

## `current_user` carry-forward from Task 18

Resolved with no change. The SP's `current_user()` is its application id (the bare UUID), which is exactly the value `post_deploy_grants.sh` already inserts into `discipline_access`, so `drawing_register_visible=1200`.

## Vector Search grant note (for Task 24)

The SP queried the index directly, so nothing needs adding. If a future redeploy recreates the index and the log shows `vector_search fallback to SQL ... needs CAN_QUERY on the index`, grant the SP SELECT on `mfg_mc_se_sa.bluerridge_agents.code_excerpts_vs` (and CAN_QUERY on endpoint `bluerridge_vs` if required); the API keeps working through the SQL fallback meanwhile.
