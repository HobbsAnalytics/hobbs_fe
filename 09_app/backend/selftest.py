"""Startup self-test: proves service-principal access to every data source, in logs, without exposing data.

One line per source on the ``bluerridge`` logger; counts and identities only (no rows, tokens or credentials).
Runs in a background thread so it never delays or breaks startup. Read with ``databricks apps logs``.
"""
import logging
import threading

from backend import config, lakebase, vector_search, volume, warehouse

logger = logging.getLogger("bluerridge.selftest")

TABLES = ("kpi_daily", "compliance_findings", "risk_forecast", "schedule_overdue", "daily_brief")
KNOWN_PDF = "BRL-PIP-ISO-0004.pdf"
KNOWN_LABEL = "ASME B31.3 §322"


def _fail(what: str, e: Exception) -> None:
    logger.warning("selftest %s FAILED %s: %s", what, type(e).__name__, str(e)[:200])


def run() -> bool:
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
