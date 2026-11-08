"""Compliance summary and paginated findings (Lakebase). The as-of week is fixed by the demo's anchor date."""
from typing import Literal

from fastapi import APIRouter, Query

from backend import lakebase

router = APIRouter()
S = "bluerridge_app"
T = f"{S}.compliance_findings_synced"
WEEK_START, WEEK_END = "2026-10-31", "2026-11-06"
MAX_LIMIT = 200


def _bbox(v):
    if v is None:
        return None
    try:
        return [float(x) for x in v]
    except (TypeError, ValueError):
        return None


@router.get("/compliance/summary")
def compliance_summary() -> dict:
    week = (WEEK_START, WEEK_END)
    # drawing-level: FAIL if any finding failed, else REVIEW if any needs review, else PASS
    levels = lakebase.query(
        f"SELECT status, count(*) AS n FROM (SELECT drawing_id, CASE WHEN bool_or(status = 'FAIL') THEN 'FAIL' "
        f"WHEN bool_or(status = 'REVIEW') THEN 'REVIEW' ELSE 'PASS' END AS status FROM {T} "
        f"WHERE review_date BETWEEN %s AND %s GROUP BY drawing_id) d GROUP BY status", week)
    n = {r["status"]: r["n"] for r in levels}
    by_cite = lakebase.query(
        f"SELECT citation, count(*) AS fails FROM {T} WHERE status = %s AND review_date BETWEEN %s AND %s "
        f"GROUP BY citation ORDER BY fails DESC, citation", ("FAIL",) + week)
    return {
        "week": {"start": WEEK_START, "end": WEEK_END},
        "reviewed": sum(n.values()), "passed": n.get("PASS", 0), "failed": n.get("FAIL", 0), "review": n.get("REVIEW", 0),
        "fails_by_citation": [{"citation": r["citation"], "count": r["fails"]} for r in by_cite],
    }


@router.get("/compliance/findings")
def compliance_findings(
    scope: Literal["week", "all"] = "week",
    status: Literal["FAIL", "REVIEW"] = "FAIL",
    limit: int = Query(50, ge=1),
    offset: int = Query(0, ge=0),
) -> dict:
    limit = min(limit, MAX_LIMIT)
    where, params = "status = %s", [status]
    if scope == "week":
        where += " AND review_date BETWEEN %s AND %s"
        params += [WEEK_START, WEEK_END]
    total = lakebase.query(f"SELECT count(*) AS total FROM {T} WHERE {where}", tuple(params))[0]["total"]
    rows = lakebase.query(
        f"SELECT drawing_id, finding_id, status, severity, citation, reason, evidence_text, page_num, bbox, "
        f"bbox_source, review_date FROM {T} WHERE {where} "
        f"ORDER BY review_date DESC, drawing_id, finding_id LIMIT %s OFFSET %s", tuple(params + [limit, offset]))
    items = [{**r, "bbox": _bbox(r["bbox"])} for r in rows]
    return {"items": items, "total": total, "limit": limit, "offset": offset, "scope": scope, "status": status}
