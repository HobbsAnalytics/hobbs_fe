# Backend API (Tasks 19 and 20)

All data endpoints run as the app's **service principal** (SP). None of them use the forwarded user token. Only the Genie chat, `POST /api/chat` (below), does: Genie is called **only as the signed-in user**. The chat's drawing-source enrichment reads Lakebase through the app's SP pool, the same data `GET /api/compliance/findings` already serves. Errors are always JSON `{"error", "detail"}` with 401, 404, 422, 500 or 503, never a stack trace. A Lakebase or warehouse outage returns 503.

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
| `POST /api/chat` | Genie space, **as the signed-in user** (managed Genie MCP server, with a Conversation API fallback; see below), plus Lakebase findings for sources | Server-Sent Events; 401 with no user token, 422 bad body; see "Chat (Task 20)" below |

`drawing_id` pattern: `BRL-[A-Z]{3}-[A-Z]{2,4}-[0-9]{4}` (full match). It matches all 1,200 ids in `drawing_register` (13 prefixes, e.g. `BRL-INS-PID-0052`, `BRL-ELE-GA-0023`; 1200 of 1200 checked with `RLIKE` in the warehouse).

Data layers (`09_app/backend/`): `lakebase.py` (psycopg pool; each new connection mints a fresh generated database credential, `max_lifetime` 1800 s is shorter than the credential's roughly one hour life, `sslmode=require`, parameterized `%s` queries), `warehouse.py` (Statement Execution API, named `:param` markers only, 30 s wait then cancel), `volume.py` (Files API), `vector_search.py` (exact filter plus top-k, one-time logged SQL fallback). Startup self-test: `selftest.py`, results in `outputs/endpoint_selftest.md`.

## Chat (Task 20): `POST /api/chat`

The PM's question goes to the Genie space `01f1db9edffa1a298195db2806ce45e3` **as the signed-in user** (on behalf of user, OBO), so Genie applies that PM's own Unity Catalog permissions, including the `drawing_register` row filter. Code: `backend/routes/chat.py` (the route and its SSE stream) and `backend/genie.py` (the Genie layer, which takes any `WorkspaceClient`).

**Auth.** Genie is called only with `auth.user_workspace_client(request)`, the signed-in user's client. That client is built in a FastAPI dependency, so a request without `x-forwarded-access-token` gets a **401** JSON `{"error":"unauthorized",...}` before the body is even validated. There is no service-principal fallback for Genie, and the token is never logged or echoed. The only other read is the drawing-source enrichment (below): one parameterized Lakebase query through the app's SP pool, for the same `compliance_findings_synced` rows the Compliance page shows.

**Request.** `{"message": str, "conversation_id": str | null}`:
- `message` is stripped and must be 1 to 2,000 characters.
- `conversation_id` (optional) must match `^[A-Za-z0-9_-]{1,64}$`. Send the one from an earlier `conversation` event to ask a follow-up in the same Genie conversation.
- Anything else gives a **422** `{"error":"invalid_request",...}` and Genie is not called.

**Response.** `text/event-stream` (`Cache-Control: no-cache`, `X-Accel-Buffering: no`). Every event is one line `data: <json>` followed by a blank line. In order, as each becomes available:

| Event | When |
|---|---|
| `{"type":"status","value":"running"}` | First, at once. Repeated every 15 s while Genie is still working, so idle proxies keep the stream open. |
| `{"type":"conversation","conversation_id":"..."}` | As soon as Genie returns the conversation id. |
| `{"type":"answer","text":"..."}` | Genie's text, which may be a clarifying question; Genie's query description is used if there is no text. When there is no text, no SQL and no rows: `"I'm not sure which milestones you mean — try naming a discipline or specifying 'this week'."` |
| `{"type":"sql","query":"..."}` | When Genie generated SQL. |
| `{"type":"result","columns":[...],"rows":[[...]],"row_count":n,"truncated":bool}` | When the SQL produced a result. At most 50 rows; `row_count` is Genie's total; `truncated` is true when rows were cut here or upstream. Any column whose name contains `slip_probability`, case-insensitive (e.g. `max_slip_probability`), is removed from `columns` and `rows`. |
| `{"type":"sources","items":[...]}` | Only when there is at least one source (below). |
| `{"type":"status","value":"done","transport":"mcp"\|"conversation_api"}` | Last, on success. `transport` says which Genie path answered. |
| `{"type":"status","value":"error","message":"...","transport":"mcp"\|"conversation_api"}` | Instead of the rest, on failure. `message` is a fixed, safe sentence (expired session, no access to the space, Genie unavailable, Genie could not answer, no data access, or "did not answer within 110 seconds"). It never contains a stack trace, SQL, a host or exception text. `transport` is present only when the failure came from a Genie transport; it is absent, for example, when the route's own 110 s wall clock fires. |

**Sources.**
- **Drawing items.** When a result column is named `drawing_id` (case-insensitive), up to 10 distinct, well-formed ids (`BRL-[A-Z]{3}-[A-Z]{2,4}-[0-9]{4}`) are taken from the shown rows in first-seen order. Their FAIL findings are then looked up in Lakebase with a single parameterized query (`... compliance_findings_synced WHERE status = %s AND drawing_id = ANY(%s)`). Each FAIL finding becomes `{"kind":"drawing","drawing_id","finding_id","page_num","bbox","citation"}`, with `bbox` as four floats. A drawing with no FAIL finding is still listed, with nulls, so it stays clickable. If Lakebase is down, every drawing is listed with nulls and the stream still ends with `done`.
- **Citation items.** Any of the five labels `ASME B16.5 §4.2`, `OSHA 1910.147`, `IBC 1005.1`, `ASME B31.3 §341`, `ASME B31.3 §322` found in the answer text or in a string cell becomes `{"kind":"citation","label","url":"/api/citations/<URL-encoded label>"}`, e.g. `/api/citations/ASME%20B31.3%20%C2%A7322`.

**Timeouts.** Genie polling stops at 105 s, and the route's own wall clock gives up at 110 s; both end in the `error` event. The Apps proxy caps a request at 120 s (platform behavior observed during the build, not from cited docs).

**Transport.** The app uses the **managed Genie MCP server for this space**, `POST https://<workspace>/api/2.0/mcp/genie/{space_id}`. It is in Public Preview and needs the OAuth scope `genie`, which the app's `dashboards.genie` user scope may or may not map to (unconfirmed). It is verified as the app service principal; in the one live signed-in session, MCP returned 403 and the chat answered via the Conversation API fallback (still OBO). The cause of the 403 is undiagnosed; one candidate is a scope mismatch.

The app speaks MCP's JSON-RPC `tools/call` directly:
1. Call `query_space_<space_id>` with `{query, conversation_id?}`.
2. Call `poll_response_<space_id>` with `{conversation_id, message_id}` until the status is terminal.
3. Read `structuredContent`: `textAttachments` holds the answer, `queryAttachments[].query` the SQL, `queryAttachments[].statement_response` the columns and rows, and `conversationId` the conversation.

It does not use the `databricks-mcp` client library, which brings about 108 packages (full `mlflow` among them). The **Genie Conversation API** on the same space (`w.genie.start_conversation` / `create_message` → `get_message` → `get_message_attachment_query_result`) is wired in for two cases:
- as the transport, when `GENIE_TRANSPORT=conversation_api` is set;
- as a fallback, automatically and with the same user client, only when the MCP endpoint refuses the *first* call in a way that happens before Genie can have received the question:
  - HTTP 400, 403, 404, 405, 406 or 415;
  - JSON-RPC -32700, -32600, -32601 or -32602 (parse error, invalid request, unknown method, invalid params);
  - the connection could not be opened (connect timeout, refused, DNS).

  Nothing else falls back: 5xx, 429, a non-JSON body, other JSON-RPC codes, a connection dropped after the request went out, a read timeout, or any error on a poll call. In those cases Genie may already hold the message, so they end in the safe `error` event instead of risking a second ask.

  "Never asks twice" rests on an assumption: that the server rejects a first call with one of the refusals listed above before it accepts the question. That is how HTTP 4xx and a failed connect normally behave, but the managed MCP server (Public Preview) does not document it to that level.

  **Live (Task 24).** In the one signed-in OBO session, the MCP endpoint refused the user's first `query_space` call with HTTP 403. The fallback then answered through the Conversation API (`transport=conversation_api outcome=done got_sql=True rows=85`). The service principal's self-test call goes through MCP. Evidence: `outputs/live_obo_chat.md`.

  If MCP completes with SQL but without a `statement_response`, the rows are read for that same message through the Conversation API (`get_message` → `get_message_attachment_query_result`), and a warning with key names only is logged. Genie is not asked again.

The live startup self-test, which runs as the service principal, answered through `transport=mcp`. The research and evidence are in `backend/AUTH_NOTES.md`, "Genie transport for the chat", and `outputs/chat_selftest.md`.

**Request log.** One line per chat: `chat email=… transport=… outcome=… got_sql=… rows=… elapsed_ms=…`. It never includes the question, the answer, rows or the token.

Startup self-test: Task 20 adds one line per Task 19 route (counts and the parsed `bbox` shape) and one Genie question asked as the SP through the same transport code. Results are in `outputs/chat_selftest.md`.
