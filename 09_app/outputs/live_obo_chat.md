# Live on-behalf-of (OBO) chat check (Task 24)

**Result: verified.** A signed-in user's browser session reached the deployed app. `/api/whoami` logged `auth_mode=OBO`. One `POST /api/chat` was answered by Genie as that user: outcome `done`, SQL generated, 85 result rows. The drawing the user then opened from the answer loaded its metadata and PDF.

**Transport: the Conversation API fallback, not MCP.** On this OBO request the managed Genie MCP endpoint refused the first `query_space` call with HTTP 403. The chat's guarded fallback then answered through the Genie Conversation API, with the same user client. This is the case [`../backend/AUTH_NOTES.md`](../backend/AUTH_NOTES.md#genie-transport-for-the-chat-task-20) planned for: "If the MCP endpoint rejected an OBO token's scope with a 403 on the first call, the guarded fallback would answer through the Conversation API." The service principal's call through the same MCP code path does succeed (`transport=mcp ... headline=51` in every startup self-test, [`chat_selftest.md`](chat_selftest.md)). So MCP is proven live as the SP. As the user, this session answered through the Conversation API.

The 403 was not diagnosed further. The most likely cause is that the user token's OBO scopes (`dashboards.genie`, `sql`) do not cover the managed MCP endpoint, while the SP's OAuth token is not scope-restricted in the same way. That is a hypothesis, not a finding.

> **User confirmation**, as the user reported it to the build controller: live check performed by the user in their signed-in browser on 2026-11-08 (US Central; 2026-11-09 UTC in the log). The chat answered with generated SQL, and the drawing PDFs loaded.

## What the log shows

| Field | Value | Log line |
|---|---|---|
| App / deployment | `bluerridge-pm-copilot`, deployment `01f1dbe7fb1c1b8a8ae3438d566edf44` (RUNNING; boot self-test `done ok=True` at 02:48:54Z) | `databricks apps get` / boot log |
| Signed-in user | `joseph.hobbs@databricks.com` | `bluerridge.auth: whoami email=... auth_mode=OBO` at 2026-11-09T02:54:40Z |
| `auth_mode` | **OBO**: the Apps proxy forwarded the user's access token | same line |
| Chat | `POST /api/chat` at 02:54:53Z, stream closed at 02:55:09Z | `bluerridge.chat: chat email=joseph.hobbs@databricks.com transport=conversation_api outcome=done got_sql=True rows=85 elapsed_ms=15294` |
| Transport | `conversation_api`, after `genie mcp query_space refused http_status=403` and `falling back to conversation_api` | two `WARNING bluerridge.genie` lines at 02:54:54Z |
| Status | `outcome=done`, `got_sql=True`, `rows=85`, 15.3 s | chat line |
| Drawing opened from the answer | `GET /api/drawings/BRL-ELE-GA-0842` 200 (821 bytes) and `GET /api/drawings/BRL-ELE-GA-0842/pdf` 200 (7,308 bytes) at 02:55:24 to 02:55:27Z. The page was `/drawings/BRL-ELE-GA-0842?page=0&finding=BRL-ELE-GA-0842-C01`, the deep link a drawing-source chip opens | `[APP]` and `[HTTP]` access lines |
| Unauthenticated control, the same minute | `GET /api/whoami`, `GET /api/kpi/today`, `POST /api/chat` without a session: **401** (body `{}`), from the proxy; `GET /` and `GET /health`: 302 to the workspace sign-in | `[HTTP] ... "curl/8.7.1"` lines at 02:55:51 to 02:55:53Z |

Why the chat line is an OBO line even though it does not print `auth_mode`: `POST /api/chat` builds its Genie client from the forwarded user token in a FastAPI dependency. A request without `x-forwarded-access-token` gets a 401 before the route runs, and there is no service-principal fallback (`backend/routes/chat.py`, `_user_client`; tested in `backend/tests/test_chat.py`). So a chat line with `email=` and `outcome=done` can only come from a user-token request. The `whoami ... auth_mode=OBO` line 13 seconds earlier is the same browser session.

The 85 rows equal the 85 FAIL findings of the as-of week that the startup self-test counts (`selftest route compliance_findings total=85`). That fits a question about which drawings failed this week. The question text is not logged, by design.

Which identity read what in this session:

| Call | Identity | Source |
|---|---|---|
| Genie question (`/api/chat`) | **the signed-in user** (OBO token) | Genie space `01f1db9edffa1a298195db2806ce45e3`, through the Conversation API this time |
| Chat drawing-source enrichment | app service principal | Lakebase `compliance_findings_synced` |
| `/api/kpi/today`, `/api/compliance/summary`, `/api/schedule/overdue`, `/api/brief/today`, `/api/risk/top` | app service principal | Lakebase synced tables |
| `/api/drawings/{id}` | app service principal | SQL warehouse (`drawing_register`, UC row filter applies; the SP is mapped to `*`) + Lakebase findings |
| `/api/drawings/{id}/pdf` | app service principal | UC Volume `bluerridge_landing.drawings` (path read from `drawing_register`) |

## Log excerpt (scrubbed)

From `databricks apps logs bluerridge-pm-copilot --profile DEFAULT --tail-lines 400 --follow --timeout 25s`, read 2026-11-09 about 02:58 UTC. Scrubbing replaced the client IP with `<client-ip>`, the proxy hop with `<proxy>` and the numeric user and workspace ids with `<user-id>@<workspace-id>`. It shortened the user agent and replaced the app's own URL in referrers with `<app-url>`. Static-asset and favicon lines were dropped. Nothing else was changed. No token, cookie or credential appears in the raw log either: the app never logs one, and the proxy's access log does not print headers.

```
2026-11-09T02:54:25Z [HTTP] <client-ip> - - [09/Nov/2026:02:54:25 +0000] "GET / HTTP/1.1" 302 489 "-" "Mozilla/5.0 (Macintosh; ...) Chrome/156 Safari/537.36"
2026-11-09T02:54:39Z [APP] INFO:     <proxy> - "GET / HTTP/1.1" 200 OK
2026-11-09T02:54:39Z [HTTP] <client-ip> - <user-id>@<workspace-id> [09/Nov/2026:02:54:39 +0000] "GET / HTTP/1.1" 200 644 "https://fevm-mfg-mc-se-sa.cloud.databricks.com/" "Mozilla/5.0 (Macintosh; ...) Chrome/156 Safari/537.36"
2026-11-09T02:54:40Z [APP] INFO bluerridge.auth: whoami email=joseph.hobbs@databricks.com auth_mode=OBO
2026-11-09T02:54:40Z [APP] INFO:     <proxy> - "GET /api/whoami HTTP/1.1" 200 OK
2026-11-09T02:54:40Z [APP] INFO:     <proxy> - "GET /api/compliance/summary HTTP/1.1" 200 OK
2026-11-09T02:54:40Z [APP] INFO:     <proxy> - "GET /api/schedule/overdue HTTP/1.1" 200 OK
2026-11-09T02:54:40Z [APP] INFO:     <proxy> - "GET /api/kpi/today HTTP/1.1" 200 OK
2026-11-09T02:54:40Z [APP] INFO:     <proxy> - "GET /api/brief/today HTTP/1.1" 200 OK
2026-11-09T02:54:40Z [APP] INFO:     <proxy> - "GET /api/risk/top?limit=3 HTTP/1.1" 200 OK
2026-11-09T02:54:40Z [HTTP] <client-ip> - <user-id>@<workspace-id> [09/Nov/2026:02:54:40 +0000] "GET /api/whoami HTTP/1.1" 200 99 "<app-url>/" "Mozilla/5.0 (Macintosh; ...) Chrome/156 Safari/537.36"
2026-11-09T02:54:40Z [HTTP] <client-ip> - <user-id>@<workspace-id> [09/Nov/2026:02:54:40 +0000] "GET /api/compliance/summary HTTP/1.1" 200 327 "<app-url>/" "Mozilla/5.0 (Macintosh; ...) Chrome/156 Safari/537.36"
2026-11-09T02:54:40Z [HTTP] <client-ip> - <user-id>@<workspace-id> [09/Nov/2026:02:54:40 +0000] "GET /api/schedule/overdue HTTP/1.1" 200 1469 "<app-url>/" "Mozilla/5.0 (Macintosh; ...) Chrome/156 Safari/537.36"
2026-11-09T02:54:40Z [HTTP] <client-ip> - <user-id>@<workspace-id> [09/Nov/2026:02:54:40 +0000] "GET /api/kpi/today HTTP/1.1" 200 439 "<app-url>/" "Mozilla/5.0 (Macintosh; ...) Chrome/156 Safari/537.36"
2026-11-09T02:54:40Z [HTTP] <client-ip> - <user-id>@<workspace-id> [09/Nov/2026:02:54:40 +0000] "GET /api/brief/today HTTP/1.1" 200 888 "<app-url>/" "Mozilla/5.0 (Macintosh; ...) Chrome/156 Safari/537.36"
2026-11-09T02:54:40Z [HTTP] <client-ip> - <user-id>@<workspace-id> [09/Nov/2026:02:54:40 +0000] "GET /api/risk/top HTTP/1.1" 200 1125 "<app-url>/" "Mozilla/5.0 (Macintosh; ...) Chrome/156 Safari/537.36"
2026-11-09T02:54:53Z [APP] INFO:     <proxy> - "POST /api/chat HTTP/1.1" 200 OK
2026-11-09T02:54:54Z [APP] WARNING bluerridge.genie: genie mcp query_space refused http_status=403
2026-11-09T02:54:54Z [APP] WARNING bluerridge.genie: genie mcp refused the first call before execution (forbidden); falling back to conversation_api
2026-11-09T02:55:09Z [APP] INFO bluerridge.chat: chat email=joseph.hobbs@databricks.com transport=conversation_api outcome=done got_sql=True rows=85 elapsed_ms=15294
2026-11-09T02:55:09Z [HTTP] <client-ip> - <user-id>@<workspace-id> [09/Nov/2026:02:54:53 +0000] "POST /api/chat HTTP/1.1" 200 19695 "<app-url>/" "Mozilla/5.0 (Macintosh; ...) Chrome/156 Safari/537.36"
2026-11-09T02:55:26Z [APP] INFO:     <proxy> - "GET /api/drawings/BRL-ELE-GA-0842 HTTP/1.1" 200 OK
2026-11-09T02:55:26Z [HTTP] <client-ip> - <user-id>@<workspace-id> [09/Nov/2026:02:55:24 +0000] "GET /api/drawings/BRL-ELE-GA-0842 HTTP/1.1" 200 821 "<app-url>/drawings/BRL-ELE-GA-0842?page=0&finding=BRL-ELE-GA-0842-C01" "Mozilla/5.0 (Macintosh; ...) Chrome/156 Safari/537.36"
2026-11-09T02:55:27Z [APP] INFO:     <proxy> - "GET /api/drawings/BRL-ELE-GA-0842/pdf HTTP/1.1" 200 OK
2026-11-09T02:55:27Z [HTTP] <client-ip> - <user-id>@<workspace-id> [09/Nov/2026:02:55:26 +0000] "GET /api/drawings/BRL-ELE-GA-0842/pdf HTTP/1.1" 200 7308 "<app-url>/drawings/BRL-ELE-GA-0842?page=0&finding=BRL-ELE-GA-0842-C01" "Mozilla/5.0 (Macintosh; ...) Chrome/156 Safari/537.36"
2026-11-09T02:55:51Z [HTTP] <client-ip> - - [09/Nov/2026:02:55:51 +0000] "GET /api/whoami HTTP/1.1" 401 2 "-" "curl/8.7.1"
2026-11-09T02:55:52Z [HTTP] <client-ip> - - [09/Nov/2026:02:55:52 +0000] "GET /api/kpi/today HTTP/1.1" 401 2 "-" "curl/8.7.1"
2026-11-09T02:55:52Z [HTTP] <client-ip> - - [09/Nov/2026:02:55:52 +0000] "GET /health HTTP/1.1" 302 497 "-" "curl/8.7.1"
2026-11-09T02:55:52Z [HTTP] <client-ip> - - [09/Nov/2026:02:55:52 +0000] "GET / HTTP/1.1" 302 489 "-" "curl/8.7.1"
2026-11-09T02:55:53Z [HTTP] <client-ip> - - [09/Nov/2026:02:55:52 +0000] "POST /api/chat HTTP/1.1" 401 2 "-" "curl/8.7.1"
```

The window has no `ERROR` or `Traceback` line. The two `WARNING` lines are the designed fallback.

## What this changes in the docs

- The chat's Genie call **as the signed-in user** is verified live.
- "Genie via the managed MCP server" is verified live **as the service principal** (startup self-test). In the one live OBO session, MCP refused the user's token (403) and the Conversation API fallback answered. The UI's execution note reads the transport from the `done` event, so in this session it said "via Conversation API", not "via MCP".
- Follow-up, not done in this task: find out which scope or permission the managed MCP endpoint wants for an OBO token, and either add it to `user_api_scopes` (with re-consent) or set `GENIE_TRANSPORT=conversation_api` so that OBO chats skip the refused first call (about 1 s). Neither was changed here, because the app is deployed at HEAD and this task does not redeploy.
