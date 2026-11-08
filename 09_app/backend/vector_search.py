"""Citation lookup: exact-label query on the Vector Search index, plus top-k semantic "related".

The index ``code_excerpts_vs`` (endpoint ``bluerridge_vs``) is a Delta Sync index over ``code_excerpts``. If the SP
cannot query it (needs CAN_QUERY on the index / SELECT on it, see scripts/post_deploy_grants.sh) or the call fails, the
module falls back to SQL on ``code_excerpts`` through the warehouse and logs that once.
"""
import json
import logging
import threading
from typing import Optional

from backend import config, warehouse
from backend.auth import sp_workspace_client

logger = logging.getLogger("bluerridge.vector_search")

COLUMNS = ["citation_id", "citation_label", "title", "source", "is_paraphrase", "text"]
INDEX_NAME = f"{config.CATALOG}.{config.SCHEMA_PREFIX}_agents.code_excerpts_vs"
TABLE = f"{config.CATALOG}.{config.SCHEMA_PREFIX}_agents.code_excerpts"

_mode = "unknown"  # "vs" | "sql_fallback" | "unknown" (not tried yet)
_lock = threading.Lock()


def _reset_for_tests() -> None:
    global _mode
    _mode = "unknown"


def mode() -> str:
    return _mode


def _fall_back(err: Exception) -> None:
    global _mode
    with _lock:
        if _mode != "sql_fallback":
            _mode = "sql_fallback"
            logger.warning("vector_search fallback to SQL on code_excerpts (%s); needs CAN_QUERY on the index for the app SP",
                           type(err).__name__)


def _row(d: dict) -> dict:
    out = {c: d.get(c) for c in COLUMNS}
    if isinstance(out["is_paraphrase"], str):
        out["is_paraphrase"] = out["is_paraphrase"].lower() == "true"
    return out


def _vs_query(**kw) -> list[dict]:
    global _mode
    resp = sp_workspace_client().vector_search_indexes.query_index(
        index_name=INDEX_NAME, columns=COLUMNS, **kw)
    names = [c.name for c in resp.manifest.columns]
    rows = [_row(dict(zip(names, r))) for r in (resp.result.data_array or [])]
    _mode = "vs"
    return rows


_SELECT = f"SELECT citation_id, citation_label, title, source, is_paraphrase, text FROM {TABLE}"


def exact(label: str) -> Optional[dict]:
    if _mode != "sql_fallback":
        try:
            rows = _vs_query(filters_json=json.dumps({"citation_label": label}), query_text=label, num_results=1)
            return rows[0] if rows and rows[0]["citation_label"] == label else None
        except Exception as e:
            _fall_back(e)
    rows = warehouse.query(f"{_SELECT} WHERE citation_label = :label LIMIT 1", {"label": label})
    return _row(rows[0]) if rows else None


def related(label: str, text: str, k: int = 3) -> list[dict]:
    k = max(1, min(int(k), 10))
    if _mode != "sql_fallback":
        try:
            rows = _vs_query(query_text=text[:1000] or label, num_results=k + 1)
            return [r for r in rows if r["citation_label"] != label][:k]
        except Exception as e:
            _fall_back(e)
    rows = warehouse.query(
        f"{_SELECT} WHERE citation_label <> :label "
        f"ORDER BY (source = (SELECT max(source) FROM {TABLE} WHERE citation_label = :label)) DESC, citation_id "
        f"LIMIT {k}",
        {"label": label},
    )
    return [_row(r) for r in rows]
