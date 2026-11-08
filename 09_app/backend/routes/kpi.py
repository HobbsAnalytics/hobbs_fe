"""KPI strip, risk, overdue milestones and the daily brief. All from Lakebase synced tables (SP identity)."""
from fastapi import APIRouter, HTTPException, Query

from backend import lakebase

router = APIRouter()
S = "bluerridge_app"

RISK_COLUMNS = ("milestone_id, name, discipline, criticality, planned_end, risk_band, risk_rank, projected_slip_days, "
                "forecast_confidence_lower, forecast_confidence_upper, upstream_delay_days, upstream_milestone_id")
RISK_KEYS = [c.strip() for c in RISK_COLUMNS.split(",")]  # slip_probability is deliberately not selected or returned


@router.get("/kpi/today")
def kpi_today() -> dict:
    rows = lakebase.query(
        f"SELECT * FROM {S}.kpi_daily_synced WHERE is_current ORDER BY snapshot_date DESC LIMIT 1")
    if not rows:
        raise HTTPException(status_code=404, detail="No current KPI snapshot")
    r = rows[0]
    return {
        "project_id": r["project_id"],
        "snapshot_date": r["snapshot_date"],
        "schedule": {"status": r["schedule_status"], "milestones_hit": r["milestones_hit"],
                     "milestones_total": r["milestones_total"], "slipped_milestone_id": r["slipped_milestone_id"],
                     "slipped_days": r["slipped_days"]},
        "budget": {"total_usd": r["budget_total_usd"], "overrun_usd": r["budget_overrun_usd"],
                   "eac_pct": r["budget_eac_pct"]},
        "safety": {"days_without_incident": r["safety_days_without_incident"], "recordables_28d": r["recordables_28d"],
                   "trir_28d": r["trir_28d"]},
        "open_ncrs": {"total": r["open_ncrs"], "compliance": r["open_ncrs_compliance"],
                      "workmanship": r["open_ncrs_workmanship"]},
        "compliance_week": {"reviewed": r["compliance_reviewed_week"], "passed": r["compliance_passed_week"],
                            "failed": r["compliance_failed_week"]},
    }


@router.get("/risk/top")
def risk_top(limit: int = Query(5, ge=1)) -> dict:
    limit = min(limit, 50)
    rows = lakebase.query(
        f"SELECT {RISK_COLUMNS} FROM {S}.risk_forecast_synced ORDER BY risk_rank ASC LIMIT %s", (limit,))
    counts = {"High": 0, "Medium": 0, "Low": 0}
    for c in lakebase.query(f"SELECT risk_band, count(*) AS n FROM {S}.risk_forecast_synced GROUP BY risk_band"):
        counts[c["risk_band"]] = c["n"]
    return {"items": [{k: r[k] for k in RISK_KEYS} for r in rows], "risk_counts": counts}


@router.get("/schedule/overdue")
def schedule_overdue() -> dict:
    rows = lakebase.query(
        f"SELECT milestone_id, name, discipline, criticality, planned_end, days_late, downstream_open_count "
        f"FROM {S}.schedule_overdue_synced ORDER BY days_late DESC, milestone_id")
    items = [{**r, "status": "late" if (r["days_late"] or 0) > 0 else "due_today"} for r in rows]
    return {"items": items, "total": len(items),
            "late": sum(i["status"] == "late" for i in items),
            "due_today": sum(i["status"] == "due_today" for i in items)}


@router.get("/brief/today")
def brief_today() -> dict:
    rows = lakebase.query(
        f"SELECT brief_md, brief_date, validation_status, prompt_version, generated_at "
        f"FROM {S}.daily_brief_synced ORDER BY brief_date DESC LIMIT 1")
    if not rows:
        raise HTTPException(status_code=404, detail="No daily brief available")
    return rows[0]
