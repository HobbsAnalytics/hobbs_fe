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
- The app's own warehouse reads run as the SP, so they need no user scope.

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
