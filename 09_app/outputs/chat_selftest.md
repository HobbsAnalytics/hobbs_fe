# Chat backend: extended startup self-test (Task 20)

Task 20 extends the deployed app's background startup self-test (`09_app/backend/selftest.py`) with two stages after the Task 19 data-source checks:

1. **routes**: each Task 19 route's data function is called in-process with its default arguments. One line each, counts only. For the first FAIL finding this week, the line also gives the raw Postgres type of `bbox` next to the parsed shape the API returns.
2. **genie**: one gold-only question, "How many drawings failed this week?", sent through `genie.ask`. That is the same transport code as `POST /api/chat`, but called with the app service principal's client instead of the user's. In the chat itself, Genie is called only as the signed-in user (OBO). The chat's drawing-source enrichment reads Lakebase through the app's service-principal pool, the same data the Compliance page already serves.

Every line contains counts, types and identities only. No row content, SQL, answer text, tokens or credentials are logged.

Read with `databricks apps logs bluerridge-pm-copilot --profile DEFAULT` after `databricks bundle deploy -t demo --profile DEFAULT` and `databricks bundle run pm_copilot_app -t demo --profile DEFAULT`. App state was RUNNING, compute ACTIVE, deployment `01f1dbd6fc2e1d68846ac34bd291801a` created 2026-11-09T00:46:22Z, and `user_api_scopes` read back as `[dashboards.genie, sql]`.

Excerpt from that deployment's boot (timestamps UTC; nothing was removed, because nothing secret appears):

```
2026-11-09T00:46:46Z [APP] INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
2026-11-09T00:46:47Z [APP] INFO bluerridge.selftest: selftest lakebase kpi_daily_synced rows=90
2026-11-09T00:46:47Z [APP] INFO bluerridge.selftest: selftest lakebase compliance_findings_synced rows=1379
2026-11-09T00:46:47Z [APP] INFO bluerridge.selftest: selftest lakebase risk_forecast_synced rows=64
2026-11-09T00:46:47Z [APP] INFO bluerridge.selftest: selftest lakebase schedule_overdue_synced rows=7
2026-11-09T00:46:47Z [APP] INFO bluerridge.selftest: selftest lakebase daily_brief_synced rows=1
2026-11-09T00:46:48Z [APP] INFO bluerridge.selftest: selftest warehouse current_user=02a6516a-0d8f-49e9-8965-56e89fa12ad4 drawing_register_visible=1200
2026-11-09T00:46:49Z [APP] INFO bluerridge.selftest: selftest volume BRL-PIP-ISO-0004.pdf exists=True size=6150
2026-11-09T00:46:50Z [APP] INFO bluerridge.selftest: selftest vector_search mode=vs hits=4
2026-11-09T00:46:50Z [APP] INFO bluerridge.selftest: selftest route compliance_summary reviewed=238 failed=51
2026-11-09T00:46:50Z [APP] INFO bluerridge.selftest: selftest route compliance_findings total=85 bbox_raw_type=list bbox_pg_type=jsonb bbox_type=list bbox_len=4 bbox_floats=True
2026-11-09T00:46:50Z [APP] INFO bluerridge.selftest: selftest route risk_top n=5 high=26
2026-11-09T00:46:50Z [APP] INFO bluerridge.selftest: selftest route overdue late=6 due_today=1
2026-11-09T00:46:50Z [APP] INFO bluerridge.selftest: selftest route kpi_today ok=True
2026-11-09T00:46:50Z [APP] INFO bluerridge.selftest: selftest route brief_today ok=True
2026-11-09T00:47:04Z [APP] INFO bluerridge.selftest: selftest genie transport=mcp status=COMPLETED got_sql=True rows=1 headline=51
2026-11-09T00:47:04Z [APP] INFO bluerridge.selftest: selftest done ok=True
```

The same boot logged no `WARNING`, `ERROR` or `Traceback` lines. That means no MCP-to-Conversation-API fallback and no unparseable `bbox`.

| Check | Live result | Expected / matches |
|---|---|---|
| `compliance_summary()` | reviewed 238, failed 51 | the week's drawing-level 238 / 51 (Task 19, `API.md`) |
| `compliance_findings(scope="week", status="FAIL")` | 85 FAIL findings this week. The first one's `bbox` is a Python `list` straight from Postgres (column type `jsonb`), and the API returns it as a `list` of 4 floats. | four floats, the project convention: normalized `[x, y, w, h]`, top-left origin (what the PDF viewer draws) |
| `risk_top(limit=5)` | 5 items, 26 High | the 26 High in `risk_forecast` |
| `schedule_overdue()` | 6 late, 1 due today | the 7 rows in `schedule_overdue_synced` |
| `kpi_today()`, `brief_today()` | both return a row | |
| Genie as the SP, through the chat's transport (`transport=mcp`) | COMPLETED, SQL generated, 1 row, first numeric cell 51 | 51 drawings failed this week, the same count as `compliance_summary` and curated question 1 in `evidence/genie_qa_transcript.md` (51 failed of 238 reviewed) |

## About `bbox`

Unity Catalog describes the synced table's `bbox` column as `string`, but the Delta source is `array<double>`. Lakebase maps ARRAY to JSONB (the Lakebase synced-table type mapping), so the Postgres column is `jsonb`, and psycopg decodes it to a Python list. The live line confirms both parts: `bbox_pg_type=jsonb bbox_raw_type=list`.

So Task 19's parser already worked on live data. Task 20 hardens it anyway: `_bbox` in `routes/compliance.py` now also accepts JSON text (`"[0.1, 0.2, 0.3, 0.4]"`) and a Postgres array literal (`"{0.1,0.2,0.3,0.4}"`). It requires exactly four finite floats; anything else returns `None` and logs one warning per process. The unit tests are in `backend/tests/test_chat.py`.

## Genie as the SP

The service principal (`02a6516a-…`) has CAN_RUN on the Genie space through the app's `genie-space` resource binding, CAN_USE on the warehouse, and SELECT on `bluerridge_gold_pm`. That is enough for this gold-only question. It has no grant on `bluerridge_silver_engineering`, so the SP could not answer schedule, NCR or change-order questions. That does not matter, because `/api/chat` calls Genie as the signed-in user (OBO), never as the SP. The self-test only proves that the transport and parsing work end to end against the live space.

The OBO path itself (a PM's token through the Apps proxy) cannot be exercised headlessly: the workspace's Okta login requires a managed device. It is verified in the browser in Task 24.
