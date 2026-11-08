# Backend API (Task 19)

All data endpoints run as the app's **service principal** (SP); none use the forwarded user token (that is Genie only, Task 20). Errors are always JSON `{"error", "detail"}` with 404, 422, 500 or 503, never a stack trace. A Lakebase or warehouse outage returns 503.

| Route | Source | Notes |
|---|---|---|
| `GET /api/kpi/today` | Lakebase `kpi_daily_synced` (`is_current`) | `schedule`, `budget`, `safety`, `open_ncrs`, `compliance_week` |
| `GET /api/compliance/summary` | Lakebase `compliance_findings_synced` | drawing-level reviewed/passed/failed/review for 2026-10-31..2026-11-06 (238/187/51/0), `fails_by_citation` |
| `GET /api/compliance/findings?scope=week\|all&status=FAIL\|REVIEW&limit=50&offset=0` | Lakebase | server-side pagination, `limit` clamped to 200, returns `total`; bad enum or `limit<1` gives 422 |
| `GET /api/risk/top?limit=5` | Lakebase `risk_forecast_synced` | never returns `slip_probability`; adds `risk_counts` {High, Medium, Low} |
| `GET /api/schedule/overdue` | Lakebase `schedule_overdue_synced` | each row has `status` `late` (days_late > 0) or `due_today` |
| `GET /api/brief/today` | Lakebase `daily_brief_synced` | `brief_md, brief_date, validation_status, prompt_version, generated_at` |
| `GET /api/drawings/{drawing_id}` | warehouse `drawing_register` (row-filtered) + Lakebase findings | 422 bad id, 404 not visible |
| `GET /api/drawings/{drawing_id}/pdf` | warehouse (path lookup) + Volume Files API | `application/pdf`, `inline`; path comes from the table, must be under the drawings volume |
| `GET /api/citations/{label}` | Vector Search index `code_excerpts_vs`, SQL fallback on `code_excerpts` | exact `citation_label` (URL-decoded) plus up to 3 related; 404 unknown |

`drawing_id` pattern: `BRL-[A-Z]{3}-[A-Z]{2,4}-[0-9]{4}` (full match). It matches all 1,200 ids in `drawing_register` (13 prefixes, e.g. `BRL-INS-PID-0052`, `BRL-ELE-GA-0023`; 1200 of 1200 checked with `RLIKE` in the warehouse).

Data layers (`09_app/backend/`): `lakebase.py` (psycopg pool; each new connection mints a fresh generated database credential, `max_lifetime` 1800 s is shorter than the credential's roughly one hour life, `sslmode=require`, parameterized `%s` queries), `warehouse.py` (Statement Execution API, named `:param` markers only, 30 s wait then cancel), `volume.py` (Files API), `vector_search.py` (exact filter plus top-k, one-time logged SQL fallback). Startup self-test: `selftest.py`, results in `outputs/endpoint_selftest.md`.
