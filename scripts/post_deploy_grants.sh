#!/usr/bin/env bash
# Post-deploy grants for the Databricks App's service principal. Idempotent: safe to re-run after every deploy.
#
# Run after `databricks bundle deploy -t demo` has created the app (that is when its service principal exists) and
# once the five Lakebase synced tables are online. Runs as YOU (the deployer and Lakebase project owner), never as the SP.
#
#   (a) read the app SP's application id + display name from `databricks apps get` (service_principal_client_id,
#       service_principal_name). The application id is also what current_user() returns in the app's SQL.
#   (b) Unity Catalog grants from 06_governance/grants.sql ({app_sp} statements): USE CATALOG mfg_mc_se_sa;
#       USE SCHEMA + SELECT on bluerridge_gold_pm and bluerridge_agents; USE SCHEMA bluerridge_landing +
#       READ VOLUME bluerridge_landing.drawings
#   (c) MERGE ('<application id>', '*') into bluerridge_agents.discipline_access, so the drawing_register row filter
#       shows the app every drawing (same file)
#   (d) Postgres: make sure the SP's Lakebase role exists (create it if the platform has not), then apply
#       08_lakebase/app_grants.sql through psycopg with a freshly generated database credential for you
#   Then verify all of it (SHOW GRANTS, the mapping row, Postgres privileges) and write a markdown report.
#
# Usage:
#   scripts/post_deploy_grants.sh [--profile DEFAULT] [--app bluerridge-pm-copilot] [--out FILE [--append]]
# Example (the run committed in 09_app/outputs/post_deploy_grants_run.md):
#   scripts/post_deploy_grants.sh --profile DEFAULT --out 09_app/outputs/post_deploy_grants_run.md
#
# Needs: Databricks CLI (authenticated profile), uv (runs the Python step with databricks-sdk + psycopg), dig.
# Set PYTHON=/path/to/python to use an interpreter that already has databricks-sdk>=0.81 and psycopg 3 instead of uv.
# Never prints a credential: the database credential is generated inside the Python step and passed straight to psycopg.
set -euo pipefail

PROFILE="DEFAULT"
APP="bluerridge-pm-copilot"
BRANCH="projects/bluerridge-pm/branches/production"
ENDPOINT="$BRANCH/endpoints/primary"
DATABASE="databricks_postgres"
WAREHOUSE_ID="527214d7319cb124"
OUT=""
APPEND=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --profile) PROFILE="$2"; shift 2 ;;
        --app)     APP="$2"; shift 2 ;;
        --out)     OUT="$2"; shift 2 ;;
        --append)  APPEND=(--append); shift ;;
        -h|--help) sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "Unknown arg: $1 (see --help)" >&2; exit 1 ;;
    esac
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

json_field() {  # json_field <field> < json
    python3 -I -c 'import json,sys; v=json.load(sys.stdin).get(sys.argv[1]); print("" if v is None else v)' "$1"
}

# (a) the app's service principal
APP_JSON="$(databricks apps get "$APP" --profile "$PROFILE" -o json)"
SP_ID="$(json_field service_principal_client_id <<<"$APP_JSON")"
SP_NAME="$(json_field service_principal_name <<<"$APP_JSON")"
if [[ ! "$SP_ID" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]]; then
    echo "[grants] ERROR: app '$APP' has no service principal application id (got '$SP_ID')." >&2
    exit 1
fi
echo "[grants] app=$APP sp_application_id=$SP_ID sp_name='$SP_NAME'"

# (d, first half) the SP's Postgres role: postgres_role is the bare application id
find_role() {
    databricks postgres list-roles "$BRANCH" --profile "$PROFILE" -o json | python3 -I -c '
import json, sys
sp = sys.argv[1]
for r in json.load(sys.stdin):
    s = r.get("status", {})
    if s.get("identity_type") == "SERVICE_PRINCIPAL" and s.get("postgres_role") == sp:
        print(r["name"]); break
' "$SP_ID"
}
ROLE_RES="$(find_role)"
ROLE_CREATED="no"
if [[ -z "$ROLE_RES" ]]; then
    echo "[grants] no Postgres role for $SP_ID on $BRANCH yet; creating sp-$SP_ID"
    databricks postgres create-role "$BRANCH" --role-id "sp-$SP_ID" --profile "$PROFILE" \
        --json "{\"spec\":{\"identity_type\":\"SERVICE_PRINCIPAL\",\"postgres_role\":\"$SP_ID\",\"auth_method\":\"LAKEBASE_OAUTH_V1\"}}" >/dev/null
    ROLE_RES="$(find_role)"
    ROLE_CREATED="yes"
    [[ -n "$ROLE_RES" ]] || { echo "[grants] ERROR: role still missing after create-role" >&2; exit 1; }
fi
echo "[grants] postgres role resource: $ROLE_RES (created now: $ROLE_CREATED)"

# (b) (c) (d) and verification
if [[ -n "${PYTHON:-}" ]]; then
    RUN=("$PYTHON" -I)
else
    RUN=(uv run --no-project --quiet --with "databricks-sdk>=0.81" --with "psycopg[binary]>=3.2" python -I)
fi
ARGS=(--profile "$PROFILE" --app "$APP" --sp-id "$SP_ID" --sp-name "$SP_NAME" --warehouse-id "$WAREHOUSE_ID"
      --endpoint "$ENDPOINT" --database "$DATABASE" --pg-role "$SP_ID" --pg-role-resource "$ROLE_RES"
      --pg-role-created "$ROLE_CREATED")
[[ -n "$OUT" ]] && ARGS+=(--out "$OUT" ${APPEND[@]+"${APPEND[@]}"})
"${RUN[@]}" scripts/post_deploy_grants.py "${ARGS[@]}"
echo "[grants] done."
