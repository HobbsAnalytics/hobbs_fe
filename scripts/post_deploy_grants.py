"""Post-deploy grants for the app's service principal. Called by scripts/post_deploy_grants.sh, which resolves the SP.

Runs as the deploying user (SDK profile auth from the Databricks CLI profile), never as the SP, and is idempotent:
  (b) Unity Catalog grants: the statements in 06_governance/grants.sql that use {app_sp}
  (c) row-filter mapping: the MERGE of ('<app id>', '*') into bluerridge_agents.discipline_access (same file)
  (d) Postgres grants: 08_lakebase/app_grants.sql with ${APP_SP_ROLE} = the SP's Postgres role, via psycopg
Then it verifies all three (SHOW GRANTS, the mapping row, Postgres privileges) and writes a markdown report.

Credentials: the Lakebase database credential for the project owner is generated in-process and handed straight to
psycopg as the password. It is never printed, logged, written to a file or put in argv/env.
Needs databricks-sdk >= 0.81 (w.postgres) and psycopg 3; the shell wrapper runs this under `uv run --with ...`.
"""
import argparse
import datetime as dt
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GRANTS_SQL = ROOT / "06_governance" / "grants.sql"
PG_GRANTS_SQL = ROOT / "08_lakebase" / "app_grants.sql"
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

CATALOG = "mfg_mc_se_sa"
PG_SCHEMA = "bluerridge_app"
# (securable type, full name, privileges the SP must hold directly on it after the run)
EXPECTED_UC = [
    ("CATALOG", CATALOG, {"USE CATALOG"}),
    ("SCHEMA", f"{CATALOG}.bluerridge_gold_pm", {"USE SCHEMA", "SELECT"}),
    ("SCHEMA", f"{CATALOG}.bluerridge_agents", {"USE SCHEMA", "SELECT"}),
    ("SCHEMA", f"{CATALOG}.bluerridge_landing", {"USE SCHEMA"}),
    ("VOLUME", f"{CATALOG}.bluerridge_landing.drawings", {"READ VOLUME"}),
]


def split_sql(path: Path) -> list:
    """Same rules as 06_governance/apply.ipynb statements(): drop `--` lines, split on semicolons."""
    text = "\n".join(l for l in path.read_text().splitlines() if not l.strip().startswith("--"))
    return [s.strip() for s in text.split(";") if s.strip()]


def uc_statements(sp: str) -> list:
    out = []
    for s in split_sql(GRANTS_SQL):
        if set(re.findall(r"\{(\w+)\}", s)) == {"app_sp"}:
            out.append(s.format(app_sp=sp))
    if not out:
        raise SystemExit("no {app_sp} statements found in 06_governance/grants.sql")
    return out


def pg_statements(role: str) -> list:
    out = []
    for s in split_sql(PG_GRANTS_SQL):
        s2 = s.replace("${APP_SP_ROLE}", role)
        # The SQL already double-quotes the placeholder; a stray quote or unreplaced placeholder is a bug.
        if '""' in s2 or "${" in s2:
            raise SystemExit(f"bad substitution in app_grants.sql statement: {s2!r}")
        out.append(s2)
    return out


def one_line(s: str) -> str:
    return " ".join(s.split())


def code(s: str) -> str:
    """Markdown inline code that survives backticks inside (UC identifiers are backtick-quoted)."""
    return f"`` {s} ``" if "`" in s else f"`{s}`"


class Report:
    def __init__(self):
        self.lines = []

    def __call__(self, line: str = ""):
        print(line, flush=True)
        self.lines.append(line)


def run_uc(w, warehouse_id: str, stmt: str):
    from databricks.sdk.service.sql import StatementState

    r = w.statement_execution.execute_statement(statement=stmt, warehouse_id=warehouse_id, wait_timeout="50s")
    while r.status.state in (StatementState.PENDING, StatementState.RUNNING):
        time.sleep(2)
        r = w.statement_execution.get_statement(r.statement_id)
    if r.status.state != StatementState.SUCCEEDED:
        msg = r.status.error.message if r.status.error else r.status.state
        raise RuntimeError(f"{one_line(stmt)[:120]} -> {msg}")
    cols = [c.name for c in r.manifest.schema.columns] if r.manifest and r.manifest.schema else []
    rows = (r.result.data_array or []) if r.result else []
    return cols, rows


def pg_connect_kwargs(w, endpoint: str, database: str) -> dict:
    host = w.postgres.get_endpoint(name=endpoint).status.hosts.host
    kw = dict(host=host, port=5432, dbname=database, user=w.current_user.me().user_name,
              sslmode="require", connect_timeout=30)
    try:
        socket.getaddrinfo(host, 5432)
    except socket.gaierror:
        # macOS resolver can fail on long Lakebase hostnames; resolve with dig, keep host for TLS SNI.
        ip = subprocess.run(["dig", "+short", host], capture_output=True, text=True).stdout.split()
        ip = [x for x in ip if re.match(r"^\d+\.\d+\.\d+\.\d+$", x)]
        if not ip:
            raise
        kw["hostaddr"] = ip[0]
    return kw


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--profile", required=True)
    p.add_argument("--app", required=True)
    p.add_argument("--sp-id", required=True, help="service_principal_client_id (application id)")
    p.add_argument("--sp-name", default="")
    p.add_argument("--warehouse-id", required=True)
    p.add_argument("--endpoint", required=True, help="projects/<p>/branches/<b>/endpoints/<e>")
    p.add_argument("--database", default="databricks_postgres")
    p.add_argument("--pg-role", required=True, help="the SP's Postgres role name (postgres_role)")
    p.add_argument("--pg-role-resource", default="")
    p.add_argument("--pg-role-created", default="no")
    p.add_argument("--out", help="write the markdown report here")
    p.add_argument("--append", action="store_true", help="append to --out instead of overwriting")
    a = p.parse_args()

    if not UUID_RE.match(a.sp_id) or not UUID_RE.match(a.pg_role):
        raise SystemExit("sp id / Postgres role must be a lowercase UUID (application id)")

    import psycopg
    from databricks.sdk import WorkspaceClient

    w = WorkspaceClient(profile=a.profile)
    me = w.current_user.me().user_name
    R = Report()
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    R(f"## Run {now}")
    R()
    R(f"- Ran as `{me}` (CLI profile `{a.profile}`), warehouse `{a.warehouse_id}`.")
    R(f"- (a) App `{a.app}`: service principal application id `{a.sp_id}`, display name `{a.sp_name}`.")
    R(f"- Postgres role for the SP: `{a.pg_role}` (resource `{a.pg_role_resource}`, created by this run: {a.pg_role_created}).")
    R()

    # (b) + (c) Unity Catalog
    R("### (b) Unity Catalog grants and (c) row-filter mapping (`06_governance/grants.sql`, `{app_sp}` statements)")
    R()
    R("| # | Statement | Result |")
    R("|---|---|---|")
    for i, s in enumerate(uc_statements(a.sp_id), 1):
        cols, rows = run_uc(w, a.warehouse_id, s)
        res = "OK"
        if s.startswith("MERGE") and rows:
            res = "OK, " + ", ".join(f"{c}={v}" for c, v in zip(cols, rows[0]))
        R(f"| {i} | {code(one_line(s))} | {res} |")
    R()

    R(f"#### Verify: {code(f'SHOW GRANTS `{a.sp_id}` ON ...')}")
    R()
    R("```")
    missing = []
    for typ, name, want in EXPECTED_UC:
        cols, rows = run_uc(w, a.warehouse_id, f"SHOW GRANTS `{a.sp_id}` ON {typ} {name}")
        ix = {c: i for i, c in enumerate(cols)}
        direct = set()
        R(f"SHOW GRANTS `{a.sp_id}` ON {typ} {name}")
        for r in rows:
            R("  " + " | ".join(str(r[ix[c]]) for c in ("Principal", "ActionType", "ObjectType", "ObjectKey") if c in ix))
            if r[ix["Principal"]] == a.sp_id and r[ix["ObjectType"]] == typ:
                direct.add(r[ix["ActionType"]])
        if want - direct:
            missing.append((typ, name, sorted(want - direct)))
    R("```")
    R()
    if missing:
        R(f"**MISSING UC grants:** {missing}")
        return 1
    R("All expected direct grants are present (USE CATALOG; USE SCHEMA + SELECT on gold_pm and agents; "
      "USE SCHEMA on landing; READ VOLUME on landing.drawings).")
    R()

    cols, rows = run_uc(w, a.warehouse_id,
                        f"SELECT principal, discipline FROM {CATALOG}.bluerridge_agents.discipline_access "
                        f"WHERE principal = '{a.sp_id}' ORDER BY discipline")
    R("#### Verify: `discipline_access` rows for the SP")
    R()
    R("| principal | discipline |")
    R("|---|---|")
    for r in rows:
        R(f"| `{r[0]}` | `{r[1]}` |")
    R()
    if [list(r) for r in rows] != [[a.sp_id, "*"]]:
        R("**Expected exactly one ('<app id>', '*') row.**")
        return 1

    # (d) Postgres
    R(f"### (d) Postgres grants (`08_lakebase/app_grants.sql`, `${{APP_SP_ROLE}}` = `{a.pg_role}`)")
    R()
    kw = pg_connect_kwargs(w, a.endpoint, a.database)
    R(f"Connected to `{kw['host']}` database `{a.database}` as `{kw['user']}` with a freshly generated database "
      "credential (not shown), `sslmode=require`.")
    R()
    stmts = pg_statements(a.pg_role)
    cred = w.postgres.generate_database_credential(endpoint=a.endpoint)
    with psycopg.connect(password=cred.token, **kw) as conn:
        del cred
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (a.pg_role,))
            if cur.fetchone() is None:
                R(f"**Postgres role `{a.pg_role}` does not exist in the database.**")
                return 1
            R("| # | Statement | Result |")
            R("|---|---|---|")
            for i, s in enumerate(stmts, 1):
                cur.execute(s)
                R(f"| {i} | {code(one_line(s))} | {cur.statusmessage} |")
        conn.commit()
        R()
        with conn.cursor() as cur:
            cur.execute("SELECT has_database_privilege(%s, %s, 'CONNECT'), has_schema_privilege(%s, %s, 'USAGE')",
                        (a.pg_role, a.database, a.pg_role, PG_SCHEMA))
            db_ok, schema_ok = cur.fetchone()
            R(f"- `has_database_privilege('{a.pg_role}', '{a.database}', 'CONNECT')` = {db_ok}")
            R(f"- `has_schema_privilege('{a.pg_role}', '{PG_SCHEMA}', 'USAGE')` = {schema_ok}")
            R()
            R(f"#### Verify: `\\dp {PG_SCHEMA}.*` (access privileges; the SP's entries, `r` = SELECT)")
            R()
            cur.execute(
                """SELECT n.nspname, c.relname,
                          CASE c.relkind WHEN 'r' THEN 'table' WHEN 'v' THEN 'view' WHEN 'm' THEN 'materialized view'
                                         WHEN 'p' THEN 'partitioned table' WHEN 'f' THEN 'foreign table' END,
                          pg_get_userbyid(c.relowner),
                          coalesce(array_to_string(ARRAY(SELECT x::text FROM unnest(c.relacl) x
                                                         WHERE x::text LIKE %s || '=%%'
                                                            OR x::text LIKE '"' || %s || '"=%%'), ', '), ''),
                          has_table_privilege(%s, c.oid, 'SELECT'),
                          has_table_privilege(%s, c.oid, 'INSERT')
                     FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE n.nspname = %s AND c.relkind IN ('r', 'v', 'm', 'p', 'f')
                    ORDER BY c.relname""",
                (a.pg_role, a.pg_role, a.pg_role, a.pg_role, PG_SCHEMA))
            rows = cur.fetchall()
            R("| Schema | Name | Type | Owner | Access privileges (SP) | SP can SELECT | SP can INSERT |")
            R("|---|---|---|---|---|---|---|")
            for r in rows:
                R("| " + " | ".join(f"`{v}`" if isinstance(v, str) and v else str(v) for v in r) + " |")
            R()
            cur.execute("""SELECT table_name, privilege_type FROM information_schema.role_table_grants
                            WHERE table_schema = %s AND grantee = %s ORDER BY table_name, privilege_type""",
                        (PG_SCHEMA, a.pg_role))
            grants = cur.fetchall()
            R(f"`information_schema.role_table_grants` for the SP: {len(grants)} rows: "
              + ", ".join(f"{t}:{p}" for t, p in grants))
            R()
            synced = [r for r in rows if r[1].endswith("_synced")]
            bad = [r[1] for r in synced if not r[5] or r[6]]
            if not (db_ok and schema_ok) or len(synced) != 5 or bad:
                R(f"**Postgres verification failed** (connect={db_ok}, usage={schema_ok}, synced={len(synced)}, bad={bad}).")
                return 1
    R("Postgres: CONNECT + USAGE granted, SELECT on all five `*_synced` tables, no INSERT (read-only by design).")
    R()

    if a.out:
        out = Path(a.out)
        header = "" if (a.append and out.exists()) else (
            "# Post-deploy grants for the app service principal\n\n"
            "Output of `scripts/post_deploy_grants.sh --profile DEFAULT` (verbatim; the script prints no credentials). "
            "Each run appends one section. The SP's application id and the role names are identifiers, not secrets.\n\n")
        with out.open("a" if a.append else "w") as f:
            f.write(header + "\n".join(R.lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
