# Auth notes: on-behalf-of (OBO) user auth vs. the app service principal

Research memo written **before** `backend/auth.py` (Task 18). Researched 2026-11-08. Every claim below cites the
page or the file it came from.

## Sources read

| # | Source | What it gave us |
|---|---|---|
| D1 | Databricks Apps authorization: <https://docs.databricks.com/aws/en/dev-tools/databricks-apps/auth> | App auth vs. user auth, `x-forwarded-access-token`, the scope list, and the deprecated-scope table |
| D2 | Databricks Apps HTTP headers: <https://docs.databricks.com/aws/en/dev-tools/databricks-apps/http-headers> | The forwarded identity headers, and the fact that they are absent locally |
| D3 | `current_user` function: <https://docs.databricks.com/aws/en/sql/language-manual/functions/current_user> | For a service principal it returns "the UUID of the service principal instead of a readable name" |
| D4 | Genie in apps (developer docs): <https://developers.databricks.com/docs/lakehouse/genie> | Genie OBO needs only the Genie scope; there is no fallback to the SP; scopes can be dropped by a deploy |
| D5 | OBO GA blog: <https://www.databricks.com/blog/now-ga-building-permission-aware-databricks-apps-behalf-user-authorization> | The token is "short-lived and per-request"; fail closed; never log the token; request `genie` for Genie |
| D6 | Genie Conversation API: <https://docs.databricks.com/aws/en/genie/conversation-api> | Caller needs CAN VIEW on the space and SELECT on the data; Genie evaluates the caller's own UC permissions |
| R1 | Repo **`github.com/databricks/app-templates`** (commit `7ab7b8d`), file **`mcp-server-hello-world/server/utils.py`** | The OBO client: `WorkspaceClient(token=token, auth_type="pat")`, raising when the header is missing; SP client `WorkspaceClient()` |
| R2 | Same repo, **`agent-langgraph/agent_server/utils.py`** | Same OBO construction, `get_request_headers().get("x-forwarded-access-token")` |
| R3 | Same repo, **`appkit-genie/databricks.yml`** and **`appkit-genie/manifest.yaml`** | A Genie-on-behalf-of-user app whose only scope is `user_api_scopes: [dashboards.genie]` (no `sql`) |
| R4 | Same repo, **`streamlit-data-app-obo-user/app.py`** and **`manifest.yaml`** | OBO SQL: `sql.connect(..., access_token=user_token)` with `user_api_scopes: ["sql"]`; SP SQL: `credentials_provider=lambda: cfg.authenticate` |
| R5 | Repo **`github.com/databricks-solutions/databricks-apps-cookbook`** (commit `ef14111`), file **`streamlit/views/users_get_current.py`** | Reads all four identity headers (`X-Forwarded-Email`, `-Preferred-Username`, `-User`, `-Access-Token`) and builds `WorkspaceClient(token=..., auth_type="pat")` |
| S1 | `databricks-sdk` 0.162.0 source, `databricks/sdk/config.py`, `Config._validate` and `Config._resolve_host_metadata` | Why `auth_type="pat"` is mandatory inside an app, and the per-construction metadata probe |

## Headers (exact names)

Starlette header lookup is case-insensitive. The proxy sets these headers; a client cannot supply its own through the app URL.

| Header | Meaning | Source |
|---|---|---|
| `x-forwarded-access-token` | The signed-in user's OAuth access token. It is present only when user authorization (`user_api_scopes`) is configured. | D1, D5, R1, R2, R5 |
| `x-forwarded-email` | "The user email provided by the IdP" | D2, R5 |
| `x-forwarded-user` | "The user identifier provided by the IdP". This is an id, not necessarily a readable name. | D2, R5 |
| `x-forwarded-preferred-username` | "The user name provided by the IdP" | D2, R5 |
| `x-forwarded-host`, `x-real-ip`, `x-request-id` | Original host, client IP and request UUID | D2 |

`/api/whoami` builds `user_name` from `x-forwarded-preferred-username` and falls back to `x-forwarded-user`.

## How the token reaches the app

The browser signs in to the Apps proxy with workspace SSO. On **every** request the proxy injects the user's
token in `x-forwarded-access-token`, scoped to the consented `user_api_scopes` and to this workspace only (D1).
D5 describes the token as "short-lived and per-request". The user consents once per app and scope set (D1).

## SDK construction

```python
# OBO: build per request, never cache across requests (R1, R2, R5)
WorkspaceClient(token=request.headers["x-forwarded-access-token"], auth_type="pat")

# App service principal: DATABRICKS_HOST / DATABRICKS_CLIENT_ID / DATABRICKS_CLIENT_SECRET are injected (D1, R1)
WorkspaceClient()   # oauth-m2m, refreshes itself, safe to cache for the process
```

- **`auth_type="pat"` is required, not optional.** Inside an app the env already carries the SP's
  `DATABRICKS_CLIENT_ID`/`SECRET`. Adding `token=` makes two auth methods. `Config._validate` (S1) then raises
  `validate: more than one authorization method configured: oauth and pat` unless `auth_type` is set.
- The SQL connector equivalents are `access_token=user_token` for OBO and `credentials_provider=lambda: cfg.authenticate` for the SP (R4, D1).
- `backend/auth.py` maps these to `user_workspace_client(request)` (a 401 when the header is missing),
  `sp_workspace_client()` (an `lru_cache` singleton) and `identity(request)`. The last one only reads headers and
  never constructs a client.

## Scopes for Genie on behalf of the user

- **Genie scope.** D1 lists `genie` and maps the deprecated `dashboards.genie` to `genie`. D4 and D5 say to request
  `genie` for Genie calls. R3, the official Genie app template, still uses `dashboards.genie`. Per the controller
  ruling, `resources/app.yml` keeps `dashboards.genie`, which the platform maps to `genie`. Renaming it to
  `genie` is a safe follow-up.
- **`sql`.** Neither the docs nor the reference repo show that Genie needs it. R3 runs Genie OBO without
  `sql`. D4's only scope example is `genie`. D5 says to add SQL scopes for *direct* SQL and prefer
  `sql:restricted-query`. No page says outright that `sql` is *not* needed to fetch Genie query-result rows.
  **Decision: keep `sql` for now. Verify in T20:** run the chat once with `sql` removed. If Genie answers
  and returns result rows, drop it.
- **Task 20 outcome: `sql` stays. Least-privilege note.** Removing it can only be proven with a live OBO session:
  a PM's token through the Apps proxy, asking a question and getting rows back. The headless browser cannot sign in,
  because the workspace's Okta login enforces a managed-device check, and minting a user token by hand is outside
  this build's policy. Dropping a scope blind would risk the primary UI surface. The chat needs only `genie`
  (sources D1, M1), and every SQL statement it causes is generated and run by Genie, not by the app. So `sql` is
  wider than the code needs, and for a user it is bounded by that user's own Unity Catalog grants. **Follow-up for
  Task 24:** once a browser session works, remove `sql` from `resources/app.yml`, redeploy, restart, re-consent, and
  ask the chat one question. If rows come back, the removal stands; otherwise restore it.
- The app's own warehouse reads run as the SP, so they need no user scope.

## Genie transport for the chat (Task 20)

The user asked to "just call the Genie One MCP", so the MCP options were researched first (2026-11-08).

| # | Source | What it gave us |
|---|---|---|
| M1 | Managed MCP servers: <https://docs.databricks.com/aws/en/generative-ai/mcp/managed-mcp> | Genie Agent MCP URL `https://<host>/api/2.0/mcp/genie/{genie_space_id}`, OAuth scope `genie`. Listed under "Endpoints not governed by Unity Gateway ... These endpoints are in Public Preview". "Managed MCP Servers" must be enabled by an admin. |
| M2 | Genie Agent MCP: <https://docs.databricks.com/aws/en/agents/mcp-tools/genie-agent> | Same URL and scope; read-only. |
| M3 | Genie One MCP: <https://docs.databricks.com/aws/en/agents/mcp-tools/genie-mcp> | `https://<host>/ai-gateway/mcp-services/system.ai.genie_one_mcp?o=<workspace-id>`, GA. OAuth scope `ai-gateway`; callers need `EXECUTE` on `system.ai.genie_one_mcp`. Tools `genie_ask` / `genie_poll_response` / `genie_get_query_result`. Workspace-wide: no space argument is documented. "The Beta endpoint `/api/2.0/mcp/genie` reaches end of life on November 30, 2026". That is the old Genie One beta path, without a space id. |
| M4 | AI Bridge `databricks_ai_bridge/genie.py` (`github.com/databricks/databricks-ai-bridge`, main) | Databricks' own Python `Genie(space_id, client: WorkspaceClient)` helper uses the Conversation API REST paths, not MCP. |
| M5 | Live probe, CLI-managed auth (no token handled by hand): `databricks api post /api/2.0/mcp/genie/<space_id> --json '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' --profile DEFAULT` | Tool `query_space_<space_id>` (args `query`, optional `conversation_id`) and tool `poll_response_<space_id>` (args `conversation_id`, `message_id`). Output schema `{content:{queryAttachments:[{query, description, statement_response}], textAttachments:[str], suggestedQuestions:[str]}, conversationId, messageId, status}`. |
| M6 | Live probe `tools/call query_space` "How many drawings failed this week?" | `COMPLETED` in one call, with Genie's text ("**51** distinct drawings failed this week ..."), the SQL, and a full `statement_response`: manifest columns and `data_array` rows as protobuf-style cells `{"values":[{"string_value":"51"}]}`. "which?" returned a clarifying question (text, no SQL). A drawing listing returned `drawing_id, citation` columns and 5 rows. |
| M7 | `uv pip compile` of `databricks-mcp` | 108 packages, including full `mlflow`, `matplotlib`, `docker`, `flask`, `gunicorn`. |

**Decision: the managed Genie MCP server for this space (M1, M2) is the chat's transport.** It returns everything
the chat needs (answer text, SQL, rows, conversation id) and accepts `conversation_id` for follow-ups (M5, M6).
Its scope `genie` is the one the app already has: the platform maps `dashboards.genie` to it (D1).

- **Not Genie One (M3).** It answers across the whole workspace rather than from the curated space that scored
  10/10 + 5/5 in Task 15. It also needs the extra `ai-gateway` user scope, which means re-consent and cannot be
  verified headlessly, plus a per-user `EXECUTE` grant on `system.ai.genie_one_mcp`. The space-scoped server is the
  same Genie behind an MCP interface.
- **Not the `databricks-mcp` client library (M7).** The app speaks the same MCP JSON-RPC `tools/call` itself, one
  POST per call. The call does not go through the SDK's `api_client`: that client retries read timeouts for up to
  300 s, and a retried `query_space` would ask Genie twice. Instead the request carries the header from
  `w.config.authenticate()`, the SDK's own provider, the same pattern as the SQL connector's `credentials_provider`.
  Its read timeout is the remaining deadline, and it is never retried. The header exists only inside that request;
  it is never logged or stored.
- **Conversation API kept as a guarded fallback.** It is the same space, through `w.genie.*`, and SDK 0.162 has
  `w.genie` (the gap Task 15 hit was the serverless notebook's older SDK). It is used only when
  `GENIE_TRANSPORT=conversation_api` is set, or when the MCP endpoint refuses the first call with 403, 404, 5xx or a
  JSON-RPC protocol error; at that point no Genie message exists yet. A 401 or a timeout never falls back. The live
  self-test showed `transport=mcp` with no fallback.
- **Verified so far.** The SP, through the identical code path in the startup self-test, got `transport=mcp
  status=COMPLETED got_sql=True rows=1 headline=51` (`09_app/outputs/chat_selftest.md`). The OBO path (a PM's
  token, scope `dashboards.genie` mapping to `genie`) is verified in the browser in Task 24. If the MCP endpoint
  rejected an OBO token's scope with a 403, the guarded fallback would answer through the Conversation API, and the
  `chat ... transport=` log line would show it.

## Service principal identity for SQL (row filter)

`current_user()` run by the SP returns "the UUID of the service principal" (D3). The only UUID a service
principal has is its **application id**, which `databricks apps get` returns as `service_principal_client_id`.
The SCIM `id` is numeric, and the display name is not returned at all. So `discipline_access` gets the application id with
`'*'` (see `scripts/post_deploy_grants.sh`). T19 should confirm with one SP query, `SELECT current_user()`.

## Gotchas

1. **No header locally.** D2: "These headers are only available when the app runs inside Databricks Apps."
   Under `uvicorn --reload` or in tests, the app sees no token: `identity()` reports `auth_mode: "SP"`, and
   `user_workspace_client()` returns 401. It fails closed and never falls back to the SP (D4, D5).
2. **Token expiry.** The token is short-lived and per-request (D5). Read it from each request, never store it in
   a global, cache or session, and never build an OBO client at startup. The Apps proxy has a 120 s request cap,
   which bounds any single Genie poll loop.
3. **Never log the token.** That covers `print`, logs and responses (D5). The app log records only `email` and `auth_mode`.
4. **Scopes can disappear.** D4: "Adding a new resource to the app can silently drop existing `user_api_scopes`".
   Re-check `databricks apps get ... -o json` → `user_api_scopes` after every deploy.
5. **Scope changes.** Users re-consent when the scope set changes (D1). A token issued earlier carries the old scopes.
   After editing `user_api_scopes`: redeploy, **restart the app**, then reload the app in a fresh browser session.
   This is a precaution from field experience; D1 does not say it outright.
6. **Admin allowlist.** If a workspace admin disallows a scope, the app "cannot be started, deployed, or updated"
   until the scope is removed (D1, D5).
7. **Per-request cost.** Every `WorkspaceClient(...)` construction makes one best-effort
   `/.well-known/databricks-config` probe (S1, uncached). That is fine for one Genie call per request. Do not build
   OBO clients in a tight loop.
8. **Scopes are a ceiling, not a grant.** The user still needs CAN VIEW on the space and SELECT on the tables (D6),
   and Genie applies that user's row filter on `drawing_register`.
