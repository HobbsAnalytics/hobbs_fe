"""Startup self-test: proves the deployed app works as its service principal, in logs, without exposing data.

Three stages, one ``selftest ...`` line per check on the ``bluerridge`` logger; counts, types and identities only (no
row content, SQL, answer text, tokens or credentials). Runs in a background thread so it never delays or breaks
startup. Read with ``databricks apps logs``.

1. sources: every backing store (Lakebase synced tables, warehouse row filter, Volume, Vector Search) (Task 19).
2. routes: each Task 19 route's data function called in-process with its default arguments, plus the raw Postgres
   type of a FAIL finding's ``bbox`` next to the parsed shape the API returns (Task 20).
3. genie: one gold-only question through ``genie.ask``, the same transport code path as /api/chat, with the SP's
   client in place of the user's (Task 20). In the chat, Genie is called only as the signed-in user; the chat's
   drawing-source enrichment reads Lakebase through the app's SP pool (the same data the Compliance page serves).
"""
import logging
import threading

from fastapi import HTTPException

from backend import config, genie, lakebase, vector_search, volume, warehouse
from backend.auth import sp_workspace_client
from backend.routes import compliance, kpi

logger = logging.getLogger("bluerridge.selftest")

TABLES = ("kpi_daily", "compliance_findings", "risk_forecast", "schedule_overdue", "daily_brief")
KNOWN_PDF = "BRL-PIP-ISO-0004.pdf"
KNOWN_LABEL = "ASME B31.3 §322"
GENIE_QUESTION = "How many drawings failed this week?"


def _fail(what: str, e: Exception) -> None:
    logger.warning("selftest %s FAILED %s: %s", what, type(e).__name__, str(e)[:200])


def run_sources() -> bool:
    ok = True
    for t in TABLES:
        name = f"{t}_synced"
        try:
            n = lakebase.query(f"SELECT count(*) AS n FROM bluerridge_app.{name}")[0]["n"]
            logger.info("selftest lakebase %s rows=%s", name, n)
        except Exception as e:
            ok = False
            _fail(f"lakebase {name}", e)
    try:
        r = warehouse.query(
            f"SELECT current_user() AS current_user, "
            f"(SELECT count(*) FROM {config.CATALOG}.{config.SCHEMA_PREFIX}_gold_pm.drawing_register) AS n")[0]
        logger.info("selftest warehouse current_user=%s drawing_register_visible=%s", r["current_user"], r["n"])
        ok = ok and int(r["n"]) == 1200
    except Exception as e:
        ok = False
        _fail("warehouse", e)
    try:
        exists, size = volume.stat(f"/Volumes/{config.CATALOG}/{config.SCHEMA_PREFIX}_landing/drawings/{KNOWN_PDF}")
        logger.info("selftest volume %s exists=%s size=%s", KNOWN_PDF, exists, size)
        ok = ok and exists
    except Exception as e:
        ok = False
        _fail("volume", e)
    try:
        hit = vector_search.exact(KNOWN_LABEL)
        rel = vector_search.related(KNOWN_LABEL, (hit or {}).get("text") or KNOWN_LABEL, 3) if hit else []
        hits = (1 if hit else 0) + len(rel)
        logger.info("selftest vector_search mode=%s hits=%s", vector_search.mode(), hits)
        ok = ok and hit is not None
    except Exception as e:
        ok = False
        _fail("vector_search", e)
    return ok


def _route(name: str, fn) -> bool:
    try:
        line = fn()
        logger.info("selftest route %s %s", name, line)
        return True
    except HTTPException as e:
        logger.warning("selftest route %s FAILED HTTPException status=%s", name, e.status_code)
    except Exception as e:
        _fail(f"route {name}", e)
    return False


def _summary() -> str:
    s = compliance.compliance_summary()
    return f"reviewed={s['reviewed']} failed={s['failed']}"


def _findings() -> str:
    f = compliance.compliance_findings(scope="week", status="FAIL", limit=1, offset=0)
    if not f["items"]:
        raise ValueError(f"no FAIL finding this week (total={f['total']})")
    first = f["items"][0]
    raw = lakebase.query(f"SELECT bbox, pg_typeof(bbox)::text AS pg_type FROM {compliance.T} WHERE finding_id = %s",
                         (first["finding_id"],))
    raw_value, pg_type = (raw[0]["bbox"], raw[0]["pg_type"]) if raw else (None, "none")
    parsed = first["bbox"]
    floats = isinstance(parsed, list) and len(parsed) == 4 and all(isinstance(x, float) for x in parsed)
    line = (f"total={f['total']} bbox_raw_type={type(raw_value).__name__} bbox_pg_type={pg_type} "
            f"bbox_type={type(parsed).__name__} bbox_len={len(parsed) if isinstance(parsed, list) else 0} "
            f"bbox_floats={floats}")
    if not floats:
        raise ValueError(line)
    return line


def _risk() -> str:
    r = kpi.risk_top(limit=5)
    return f"n={len(r['items'])} high={r['risk_counts'].get('High', 0)}"


def _overdue() -> str:
    o = kpi.schedule_overdue()
    return f"late={o['late']} due_today={o['due_today']}"


def _kpi() -> str:
    return f"ok={bool(kpi.kpi_today().get('snapshot_date'))}"


def _brief() -> str:
    return f"ok={bool(kpi.brief_today().get('brief_date'))}"


def run_routes() -> bool:
    results = [_route(name, fn) for name, fn in (
        ("compliance_summary", _summary), ("compliance_findings", _findings), ("risk_top", _risk),
        ("overdue", _overdue), ("kpi_today", _kpi), ("brief_today", _brief))]
    return all(results)


def run_genie() -> bool:
    try:
        t = genie.ask(sp_workspace_client(), GENIE_QUESTION)
    except genie.GenieError as e:
        logger.warning("selftest genie FAILED %s kind=%s", type(e).__name__, e.kind)
        return False
    except Exception as e:
        logger.warning("selftest genie FAILED %s", type(e).__name__)
        return False
    logger.info("selftest genie transport=%s status=%s got_sql=%s rows=%s headline=%s",
                t.transport, t.status, bool(t.sql), len(t.rows), t.headline())
    return bool(t.sql) and t.headline() is not None


def run() -> bool:
    sources_ok = run_sources()
    routes_ok = run_routes()
    genie_ok = run_genie()
    ok = sources_ok and routes_ok and genie_ok
    logger.info("selftest done ok=%s", ok)
    return ok


def start_background() -> threading.Thread:
    t = threading.Thread(target=_guarded, name="selftest", daemon=True)
    t.start()
    return t


def _guarded() -> None:
    try:
        run()
    except Exception as e:  # never take the app down
        _fail("run", e)
