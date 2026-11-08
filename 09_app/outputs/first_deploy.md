# First deploy of the Databricks App (Task 18)

The app's first real deploy, done on 2026-11-08 from commit `50ef2e0` (OBO auth + `/api/whoami`) plus a fresh `npm run build`.
The service principal's grants were applied right after it (see [`post_deploy_grants_run.md`](post_deploy_grants_run.md)).

## The app

| Field | Value |
|---|---|
| Name | `bluerridge-pm-copilot` (bundle key `pm_copilot_app`, `resources/app.yml`) |
| URL | <https://bluerridge-pm-copilot-7474644652812129.aws.databricksapps.com> |
| App status | **RUNNING** ("App has status: App is running") |
| Compute status | **ACTIVE** ("App compute is running.") |
| Active deployment | `01f1dba650961099b22db2041fb75a05`, mode SNAPSHOT, **SUCCEEDED** ("App started successfully"), created 2026-11-08T18:57:58Z |
| Source | `/Workspace/Users/joseph.hobbs@databricks.com/.bundle/bluerridge_pm_copilot/demo/files/09_app` |
| Service principal | application id `02a6516a-0d8f-49e9-8965-56e89fa12ad4`, display name `app-p3l9xk bluerridge-pm-copilot`, SCIM id `76600305063916` |
| `user_api_scopes` | `dashboards.genie`, `sql` (accepted, so user authorization is enabled in this workspace) |
| `effective_user_api_scopes` | `dashboards.genie`, `iam.access-control:read`, `iam.current-user:read`, `sql` |

**Resource bindings, as the platform resolved them.** The Task 17 `${resources...}` references resolved at deploy, so no literal-id fallback was needed:

| Resource name (`valueFrom`) | Binding | Permission |
|---|---|---|
| `sql-warehouse` | warehouse `527214d7319cb124` | CAN_USE |
| `postgres` | branch `projects/bluerridge-pm/branches/production`, database `.../databases/databricks-postgres` | CAN_CONNECT_AND_CREATE |
| `genie-space` | space `01f1db9edffa1a298195db2806ce45e3` ("Blue Ridge LNG — PM Co-Pilot (synthetic)") | CAN_RUN |
| `drawings-volume` | VOLUME `mfg_mc_se_sa.bluerridge_landing.drawings` | READ_VOLUME |

Binding `postgres` also made the platform create the SP's Lakebase role, `projects/bluerridge-pm/branches/production/roles/dbrx-apps-02a6516a-0d8f-49e9-8965-56e89fa12ad4` (`postgres_role` = the application id, `LAKEBASE_OAUTH_V1`), so no `create-role` was needed.

## Commands and their results

```text
$ cd 09_app/frontend && npm ci && npm run build
dist/index.html                   0.64 kB │ gzip:  0.43 kB
dist/assets/index-CUvYZqqx.css   11.13 kB │ gzip:  2.93 kB
dist/assets/index-DI8nU3S0.js   201.15 kB │ gzip: 64.38 kB
✓ built in 1.03s

$ databricks bundle validate --profile DEFAULT
Validation OK!

$ databricks bundle plan -t demo --profile DEFAULT
create apps.pm_copilot_app
Plan: 1 to add, 0 to change, 0 to delete, 14 unchanged

$ databricks bundle deploy -t demo --profile DEFAULT
Uploading bundle files to /Workspace/Users/joseph.hobbs@databricks.com/.bundle/bluerridge_pm_copilot/demo/files...
Created apps.pm_copilot_app
Files: 39 uploaded, 2 deleted
Resources: 1 created, 0 changed, 0 deleted, 14 unchanged

$ databricks apps get bluerridge-pm-copilot --profile DEFAULT -o json     # right after deploy
compute_status STOPPED "Start the app compute to deploy the app." / app_status UNAVAILABLE

$ databricks bundle run pm_copilot_app -t demo --profile DEFAULT       # starts compute, then deploys the source
✓ Starting the app bluerridge-pm-copilot
✓ App is started!
✓ Preparing source code for new app deployment.
✓ Downloading source code from /Workspace/Users/02a6516a-0d8f-49e9-8965-56e89fa12ad4/src/01f1dba650961099b22db2041fb75a05
✓ Installing packages...
✓ App started successfully
You can access the app at https://bluerridge-pm-copilot-7474644652812129.aws.databricksapps.com

$ databricks apps get bluerridge-pm-copilot --profile DEFAULT -o json
app_status RUNNING / compute_status ACTIVE / active_deployment 01f1dba650961099b22db2041fb75a05 SUCCEEDED
```

As the databricks-apps skill warns, a bare `bundle deploy` leaves a new app STOPPED with no deployment. `bundle run pm_copilot_app` starts it.

## Boot log (`databricks apps logs bluerridge-pm-copilot --profile DEFAULT`)

The excerpt drops the per-file "Updated file" lines and the pip progress bars. The full log was grepped for `token`, `dapi`, `eyJ`,
`Bearer`, `password`, `secret`, `error` and `Traceback`, and nothing matched. The client IP in the `[HTTP]` lines is replaced with `<client-ip>`.

```text
2026-11-08T18:57:45Z [SYSTEM] [INFO] Starting Databricks Apps runtime...
2026-11-08T18:58:08Z [BUILD] [INFO] Starting deployment 01f1dba650961099b22db2041fb75a05...
2026-11-08T18:58:08Z [BUILD] [INFO] Downloading source code from /Workspace/Users/02a6516a-0d8f-49e9-8965-56e89fa12ad4/src/01f1dba650961099b22db2041fb75a05
2026-11-08T18:58:12Z [BUILD] [INFO] Updated file: python/source_code/frontend/dist/index.html
2026-11-08T18:58:12Z [BUILD] [INFO] Updated file: python/source_code/backend/routes/whoami.py
2026-11-08T18:58:13Z [BUILD] [INFO] Updated file: python/source_code/frontend/dist/assets/index-DI8nU3S0.js
2026-11-08T18:58:14Z [BUILD] Requirement already satisfied: fastapi>=0.115.0 in ./.venv/lib/python3.11/site-packages (from -r requirements.txt (line 1)) (0.115.0)
2026-11-08T18:58:14Z [BUILD] Requirement already satisfied: uvicorn>=0.30.0 in ./.venv/lib/python3.11/site-packages (from uvicorn[standard]>=0.30.0->-r requirements.txt (line 2)) (0.30.6)
2026-11-08T18:58:17Z [BUILD]     Found existing installation: databricks-sdk 0.33.0
2026-11-08T18:58:18Z [BUILD] Successfully installed databricks-sdk-0.162.0 psycopg-3.3.8 psycopg-binary-3.3.8 psycopg-pool-3.3.3
2026-11-08T18:58:19Z [BUILD] [INFO] Requirements installed successfully.
2026-11-08T18:58:19Z [BUILD] [INFO] Starting app with command: [uvicorn backend.main:app --host 0.0.0.0 --port 8000]
2026-11-08T18:58:21Z [BUILD] [INFO] Deployment 01f1dba650961099b22db2041fb75a05 ended in 12.669695853s
2026-11-08T18:58:21Z [BUILD] [INFO] Deployment successful
2026-11-08T18:58:21Z [APP] INFO:     Started server process [76]
2026-11-08T18:58:21Z [APP] INFO:     Waiting for application startup.
2026-11-08T18:58:21Z [APP] INFO:     Application startup complete.
2026-11-08T18:58:21Z [APP] INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
2026-11-08T19:00:58Z [HTTP] <client-ip> - - [08/Nov/2026:19:00:58 +0000] "GET /api/whoami HTTP/1.1" 401 2 "-" "Mozilla/5.0 (Macintosh; ...) Chrome/156.0.0.0 Safari/537.36"
2026-11-08T19:01:16Z [HTTP] <client-ip> - - [08/Nov/2026:19:01:16 +0000] "GET / HTTP/1.1" 302 489 "-" "Mozilla/5.0 (Macintosh; ...) Chrome/156.0.0.0 Safari/537.36"
```

The boot is clean: uvicorn is on port 8000, the literal port from Task 17's `app.yaml` fix, and the platform's default
`databricks-sdk` 0.33.0 was upgraded to 0.162.0, the newest release matching `requirements.txt`'s `databricks-sdk>=0.60.0`.
(Task 19 note: `w.postgres` needs >= 0.81, so the floor should be raised when T19 adds the Lakebase client.)
The `[HTTP]` lines are the Apps proxy's access log for the browser attempt below. The 401 and the 302 come from the
proxy, not the app: there is no `[APP] ... bluerridge.auth: whoami` line, so the request never reached the backend.

## Scope decision

**`dashboards.genie` stays; `sql` stays, verify in T20.** Evidence is in [`backend/AUTH_NOTES.md`](../backend/AUTH_NOTES.md), "Scopes for Genie on behalf of the user". In short:

- The docs list `genie` as the current scope and map `dashboards.genie` to it. The official `databricks/app-templates/appkit-genie` app runs Genie on behalf of the user with only `dashboards.genie`. The developer Genie guide uses only `genie`.
- No source says `sql` is required for Genie, and none says outright that it is not needed to fetch Genie query-result rows. So, per the controller ruling, it stays for now. T20 removes it, redeploys, restarts, and confirms that Genie answers with rows.
- After deploy, the platform reports `user_api_scopes` = `[dashboards.genie, sql]`, so the scopes survived the deploy (AUTH_NOTES gotcha 4).

## Live `/api/whoami` check: deferred to Task 24

What was tried, in order (chrome-devtools MCP, a new Chrome page):

1. `GET <app-url>/api/whoami` → **HTTP 401, body `{}`**, `content-type: application/json`, with no cookies for the app domain.
   The Apps proxy refuses an unauthenticated API call; it does not redirect it.
2. `GET <app-url>/` → 302 to `https://fevm-mfg-mc-se-sa.cloud.databricks.com/login.html?next_url=/oidc/oauth2/v2.0/authorize?...redirect_uri=<app-url>/.auth/callback...`, a "Log in / Continue with SSO" page.
3. "Continue with SSO" → `databricks.okta.com/app/databricks/.../sso/saml`, and Okta refused the device:
   *"Your device doesn't meet the security requirements. To sign in, make the following updates. Then, access the app again.
   You must be on a Managed Chrome Profile"*.

The browser the MCP drives is not the user's managed Chrome profile, so it cannot pass Okta's device check, and a
Playwright browser would fail the same way. Per the session's credentials policy there was **no token workaround**
(no `databricks auth token`, no hand-built `Authorization: Bearer` call to the `/api/` route). The page was closed.

**Task 24:** in the user's managed Chrome profile, open `<app-url>/api/whoami` (accept the scope-consent prompt the first time). Expect
`{"email": "joseph.hobbs@databricks.com", "user_name": "...", "auth_mode": "OBO"}`, then save
`evidence/app_screenshots/00_whoami_obo.png`, and look for the matching app-log line
`INFO bluerridge.auth: whoami email=joseph.hobbs@databricks.com auth_mode=OBO` (it never contains the token).

Proven so far: the deployed code and the unit tests (13 whoami/auth tests, a planted token is never in the response or
the log). The proxy demonstrably gates `/api/*` behind workspace SSO.
