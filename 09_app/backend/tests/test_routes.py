"""Data endpoints (Task 19) with the data layers mocked: response shapes, validation, pagination, errors.

Every layer (lakebase / warehouse / volume / vector_search) is monkeypatched at the module attribute the routes call,
so no network and no credentials are involved.
"""
import datetime as dt
import io

import pytest
from fastapi.testclient import TestClient

from backend import lakebase, vector_search, volume, warehouse
from backend.errors import DataUnavailable
from backend.main import create_app

KPI_ROW = {
    "project_id": "BRL-PH2", "snapshot_date": dt.date(2026, 11, 6), "is_current": True,
    "schedule_status": "on_track", "milestones_hit": 6, "milestones_total": 11,
    "slipped_milestone_id": "MS-281", "slipped_days": 4,
    "budget_total_usd": 208700000.0, "budget_overrun_usd": 4800000.0, "budget_eac_pct": 2.3,
    "safety_days_without_incident": 28, "recordables_28d": 0, "trir_28d": 0.0,
    "open_ncrs": 24, "open_ncrs_compliance": 9, "open_ncrs_workmanship": 15,
    "compliance_reviewed_week": 238, "compliance_passed_week": 187, "compliance_failed_week": 51,
}

FINDING = {
    "drawing_id": "BRL-PIP-ISO-0004", "finding_id": "BRL-PIP-ISO-0004-C01", "status": "FAIL", "severity": "high",
    "citation": "ASME B31.3 §322", "reason": "r", "evidence_text": "e", "page_num": 0,
    "bbox": ["0.1", "0.2", "0.3", "0.4"], "bbox_source": "ground_truth", "review_date": dt.date(2026, 11, 5),
    "volume_path": "/Volumes/mfg_mc_se_sa/bluerridge_landing/drawings/BRL-PIP-ISO-0004.pdf",
}

RISK_ROW = {
    "milestone_id": "MS-335", "name": "Hydrotest", "discipline": "piping", "criticality": "critical",
    "planned_end": dt.date(2026, 12, 1), "risk_band": "High", "risk_rank": 1, "projected_slip_days": 12.5,
    "forecast_confidence_lower": 8.0, "forecast_confidence_upper": 17.0, "upstream_delay_days": 3.0,
    "upstream_milestone_id": "MS-300", "slip_probability": 0.91,
}

DRAWING_ROW = {
    "drawing_id": "BRL-PIP-ISO-0004", "discipline": "piping", "revision": "B", "drawing_type": "ISO",
    "volume_path": "/Volumes/mfg_mc_se_sa/bluerridge_landing/drawings/BRL-PIP-ISO-0004.pdf",
    "latest_review_date": dt.date(2026, 11, 5), "latest_status": "FAIL", "fail_count": 1,
}


class FakeLake:
    """Dispatches on SQL text. Records every (sql, params) call."""

    def __init__(self):
        self.calls = []
        self.fail = False

    def __call__(self, sql, params=None):
        self.calls.append((sql, params))
        if self.fail:
            raise DataUnavailable("Lakebase is unreachable")
        s = " ".join(sql.split())
        if "kpi_daily_synced" in s:
            return [dict(KPI_ROW)]
        if "count(*) AS total" in s and "compliance_findings_synced" in s:
            return [{"total": 77}]
        if "GROUP BY citation" in s:
            return [{"citation": "ASME B31.3 §322", "fails": 30}, {"citation": "IBC 1005.1", "fails": 8}]
        if "GROUP BY drawing_id" in s:
            return [{"status": "PASS", "n": 187}, {"status": "FAIL", "n": 51}]
        if "compliance_findings_synced" in s:
            return [dict(FINDING)]
        if "GROUP BY risk_band" in s:
            return [{"risk_band": "High", "n": 26}, {"risk_band": "Medium", "n": 20}, {"risk_band": "Low", "n": 18}]
        if "risk_forecast_synced" in s:
            return [dict(RISK_ROW)]
        if "schedule_overdue_synced" in s:
            return [
                {"milestone_id": "MS-281", "name": "A", "discipline": "piping", "criticality": "high",
                 "planned_end": dt.date(2026, 10, 22), "days_late": 15, "downstream_open_count": 2},
                {"milestone_id": "MS-299", "name": "B", "discipline": "piping", "criticality": "high",
                 "planned_end": dt.date(2026, 11, 6), "days_late": 0, "downstream_open_count": 0},
            ]
        if "daily_brief_synced" in s:
            return [{"brief_md": "# Brief", "brief_date": dt.date(2026, 11, 6), "validation_status": "PASSED",
                     "prompt_version": "v3", "generated_at": dt.datetime(2026, 11, 6, 8, 0)}]
        raise AssertionError(f"unexpected SQL: {s}")


class FakeWarehouse:
    def __init__(self, rows=None):
        self.rows = [dict(DRAWING_ROW)] if rows is None else rows
        self.calls = []
        self.fail = False

    def __call__(self, sql, params=None):
        self.calls.append((sql, params))
        if self.fail:
            raise DataUnavailable("SQL warehouse is unreachable")
        return self.rows


@pytest.fixture()
def lake(monkeypatch):
    f = FakeLake()
    monkeypatch.setattr(lakebase, "query", f)
    return f


@pytest.fixture()
def wh(monkeypatch):
    f = FakeWarehouse()
    monkeypatch.setattr(warehouse, "query", f)
    return f


@pytest.fixture()
def client(tmp_path, monkeypatch):
    (tmp_path / "index.html").write_text("<html>SPA</html>")
    # The lifespan self-test must not touch real services in route tests.
    monkeypatch.setenv("BLUERRIDGE_SELFTEST", "off")
    return TestClient(create_app(static_dir=tmp_path), raise_server_exceptions=False)


# --- KPI -------------------------------------------------------------------------------------------------------

def test_kpi_today_shape(client, lake):
    j = client.get("/api/kpi/today").json()
    assert j["schedule"]["status"] == "on_track" and j["schedule"]["milestones_total"] == 11
    assert j["schedule"]["slipped_milestone_id"] == "MS-281" and j["schedule"]["slipped_days"] == 4
    assert j["budget"]["overrun_usd"] == 4800000.0 and j["budget"]["eac_pct"] == 2.3
    assert j["safety"]["days_without_incident"] == 28
    assert j["open_ncrs"] == {"total": 24, "compliance": 9, "workmanship": 15}
    assert j["compliance_week"] == {"reviewed": 238, "passed": 187, "failed": 51}
    assert j["snapshot_date"] == "2026-11-06"
    assert "is_current" in lake.calls[0][0]


# --- compliance ------------------------------------------------------------------------------------------------

def test_compliance_summary_shape(client, lake):
    j = client.get("/api/compliance/summary").json()
    assert j["week"] == {"start": "2026-10-31", "end": "2026-11-06"}
    assert j["reviewed"] == 238 and j["passed"] == 187 and j["failed"] == 51 and j["review"] == 0
    assert j["fails_by_citation"][0] == {"citation": "ASME B31.3 §322", "count": 30}
    # dates travel as parameters, not SQL text
    assert all("2026-10-31" not in sql for sql, _ in lake.calls)


def test_findings_defaults_and_total(client, lake):
    j = client.get("/api/compliance/findings").json()
    assert j["total"] == 77 and j["limit"] == 50 and j["offset"] == 0
    assert j["scope"] == "week" and j["status"] == "FAIL"
    f = j["items"][0]
    assert f["bbox"] == [0.1, 0.2, 0.3, 0.4]
    for k in ("drawing_id", "finding_id", "status", "severity", "citation", "reason", "evidence_text", "page_num",
              "bbox_source", "review_date"):
        assert k in f
    # the status filter is a bound parameter
    assert any(p and "FAIL" in p for _, p in lake.calls)


def test_findings_limit_clamped_to_200(client, lake):
    j = client.get("/api/compliance/findings?limit=100000&offset=10&scope=all&status=REVIEW").json()
    assert j["limit"] == 200 and j["offset"] == 10 and j["scope"] == "all" and j["status"] == "REVIEW"
    page_params = lake.calls[-1][1]
    assert 200 in page_params and 10 in page_params


@pytest.mark.parametrize("qs", ["scope=bogus", "status=PASS;DROP", "limit=0", "limit=-1", "offset=-5", "limit=abc"])
def test_findings_bad_query_422(client, lake, qs):
    r = client.get(f"/api/compliance/findings?{qs}")
    assert r.status_code == 422
    assert set(r.json()) >= {"error", "detail"}


# --- risk ------------------------------------------------------------------------------------------------------

def test_risk_top_has_no_slip_probability(client, lake):
    r = client.get("/api/risk/top?limit=5")
    assert r.status_code == 200
    j = r.json()
    assert "slip_probability" not in r.text
    item = j["items"][0]
    assert set(item) == {"milestone_id", "name", "discipline", "criticality", "planned_end", "risk_band", "risk_rank",
                         "projected_slip_days", "forecast_confidence_lower", "forecast_confidence_upper",
                         "upstream_delay_days", "upstream_milestone_id"}
    assert j["risk_counts"] == {"High": 26, "Medium": 20, "Low": 18}
    assert all("slip_probability" not in sql for sql, _ in lake.calls)


def test_risk_top_limit_clamped(client, lake):
    client.get("/api/risk/top?limit=9999")
    assert lake.calls[0][1][-1] <= 50


# --- overdue / brief -------------------------------------------------------------------------------------------

def test_overdue_status_derived(client, lake):
    j = client.get("/api/schedule/overdue").json()
    assert [i["status"] for i in j["items"]] == ["late", "due_today"]
    assert j["late"] == 1 and j["due_today"] == 1 and j["total"] == 2


def test_brief_today_shape(client, lake):
    j = client.get("/api/brief/today").json()
    assert set(j) == {"brief_md", "brief_date", "validation_status", "prompt_version", "generated_at"}
    assert j["brief_date"] == "2026-11-06"


def test_brief_missing_is_404(client, monkeypatch):
    monkeypatch.setattr(lakebase, "query", lambda sql, params=None: [])
    r = client.get("/api/brief/today")
    assert r.status_code == 404 and set(r.json()) == {"error", "detail"}


# --- drawings --------------------------------------------------------------------------------------------------

def test_drawing_detail(client, lake, wh):
    j = client.get("/api/drawings/BRL-PIP-ISO-0004").json()
    assert j["drawing_id"] == "BRL-PIP-ISO-0004" and j["discipline"] == "piping"
    assert j["findings"][0]["finding_id"] == "BRL-PIP-ISO-0004-C01"
    sql, params = wh.calls[0]
    assert "BRL-PIP-ISO-0004" not in sql          # the id is a named parameter, not formatted into the SQL
    assert params == {"drawing_id": "BRL-PIP-ISO-0004"}


@pytest.mark.parametrize("bad", ["BRL-1", "..%2Fetc", "BRL-PIP-ISO-0004%27%20OR%201%3D1", "brl-pip-iso-0004",
                                 "BRL-PIP-ISO-00041", "BRL-PIP-ISO-004", "BRL-PIPE-ISO-0004", "BRL-PIP-I-0004",
                                 "%3Bdrop%20table", "BRL-PIP-ISO-0004%0A"])
def test_drawing_bad_id_422(client, lake, wh, bad):
    for suffix in ("", "/pdf"):
        r = client.get(f"/api/drawings/{bad}{suffix}")
        assert r.status_code in (404, 422)
        if "%2F" not in bad:
            assert r.status_code == 422
            assert set(r.json()) == {"error", "detail"}
    assert wh.calls == [] and lake.calls == []


def test_drawing_not_visible_is_404(client, lake, monkeypatch):
    monkeypatch.setattr(warehouse, "query", FakeWarehouse(rows=[]))
    r = client.get("/api/drawings/BRL-PIP-ISO-0004")
    assert r.status_code == 404 and r.json()["error"]


def test_pdf_uses_path_from_table_not_input(client, wh, monkeypatch):
    seen = []

    def fake_download(path):
        seen.append(path)
        return io.BytesIO(b"%PDF-1.4 fake")

    monkeypatch.setattr(volume, "open_pdf", fake_download)
    r = client.get("/api/drawings/BRL-PIP-ISO-0004/pdf")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.headers["content-disposition"].startswith("inline")
    assert r.content == b"%PDF-1.4 fake"
    assert seen == [DRAWING_ROW["volume_path"]]


def test_pdf_rejects_volume_path_outside_volume(client, monkeypatch):
    monkeypatch.setattr(warehouse, "query", FakeWarehouse(rows=[{**DRAWING_ROW, "volume_path": "/etc/passwd"}]))
    monkeypatch.setattr(volume, "open_pdf", lambda p: pytest.fail("must not open"))
    assert client.get("/api/drawings/BRL-PIP-ISO-0004/pdf").status_code == 404


def test_pdf_not_found(client, monkeypatch):
    monkeypatch.setattr(warehouse, "query", FakeWarehouse(rows=[]))
    assert client.get("/api/drawings/BRL-PIP-ISO-0004/pdf").status_code == 404


def test_pdf_missing_in_volume_is_404(client, wh, monkeypatch):
    def boom(path):
        raise FileNotFoundError(path)
    monkeypatch.setattr(volume, "open_pdf", boom)
    assert client.get("/api/drawings/BRL-PIP-ISO-0004/pdf").status_code == 404


# --- citations -------------------------------------------------------------------------------------------------

def test_citation_exact_and_related(client, monkeypatch):
    got = {}

    def exact(label):
        got["label"] = label
        return {"citation_id": "asme-b31-3-322", "citation_label": label, "title": "T", "source": "ASME B31.3",
                "is_paraphrase": False, "text": "body"}

    monkeypatch.setattr(vector_search, "exact", exact)
    monkeypatch.setattr(vector_search, "related", lambda label, text, k=3: [
        {"citation_id": f"r{i}", "citation_label": f"L{i}", "title": "t", "source": "s", "is_paraphrase": True,
         "text": "x"} for i in range(5)])
    r = client.get("/api/citations/ASME%20B31.3%20%C2%A7322")
    assert r.status_code == 200
    j = r.json()
    assert got["label"] == "ASME B31.3 §322"          # URL-decoded
    assert j["citation_label"] == "ASME B31.3 §322" and j["text"] == "body"
    assert len(j["related"]) == 3


def test_citation_unknown_404(client, monkeypatch):
    monkeypatch.setattr(vector_search, "exact", lambda label: None)
    r = client.get("/api/citations/nope")
    assert r.status_code == 404 and set(r.json()) == {"error", "detail"}


def test_citation_overlong_label_422(client):
    assert client.get("/api/citations/" + "x" * 300).status_code == 422


# --- 503, no traceback -----------------------------------------------------------------------------------------

@pytest.mark.parametrize("path", ["/api/kpi/today", "/api/compliance/summary", "/api/compliance/findings",
                                  "/api/risk/top", "/api/schedule/overdue", "/api/brief/today"])
def test_lakebase_down_is_503(client, lake, path):
    lake.fail = True
    r = client.get(path)
    assert r.status_code == 503
    assert set(r.json()) == {"error", "detail"}
    assert "Traceback" not in r.text and "File \"" not in r.text


def test_warehouse_down_is_503(client, lake, wh):
    wh.fail = True
    r = client.get("/api/drawings/BRL-PIP-ISO-0004")
    assert r.status_code == 503 and "Traceback" not in r.text


def test_unexpected_error_is_500_json_without_traceback(client, monkeypatch):
    def boom(sql, params=None):
        raise RuntimeError("secret internal detail")
    monkeypatch.setattr(lakebase, "query", boom)
    r = client.get("/api/kpi/today")
    assert r.status_code == 500
    assert "secret internal detail" not in r.text and "Traceback" not in r.text
    assert set(r.json()) == {"error", "detail"}


def test_unknown_api_path_still_404_json(client):
    assert client.get("/api/nope").status_code == 404
