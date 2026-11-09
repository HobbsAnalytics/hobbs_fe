"""Data-access layers and the startup self-test, with the Databricks SDK / psycopg mocked."""
import logging
import types
from unittest.mock import MagicMock

import pytest

from backend import lakebase, selftest, vector_search, volume, warehouse
from backend.errors import DataUnavailable


# --- warehouse -------------------------------------------------------------------------------------------------

def _resp(cols, rows, state="SUCCEEDED"):
    return types.SimpleNamespace(
        status=types.SimpleNamespace(state=types.SimpleNamespace(value=state), error=None),
        manifest=types.SimpleNamespace(schema=types.SimpleNamespace(
            columns=[types.SimpleNamespace(name=c, type_name=types.SimpleNamespace(value=t)) for c, t in cols])),
        result=types.SimpleNamespace(data_array=rows),
    )


def test_warehouse_passes_named_parameters_not_formatted_sql(monkeypatch):
    ws = MagicMock()
    ws.statement_execution.execute_statement.return_value = _resp([("drawing_id", "STRING"), ("fail_count", "INT")],
                                                                  [["BRL-PIP-ISO-0004", "2"]])
    monkeypatch.setattr(warehouse, "sp_workspace_client", lambda: ws)
    rows = warehouse.query("SELECT * FROM t WHERE drawing_id = :drawing_id", {"drawing_id": "x' OR '1'='1"})
    kwargs = ws.statement_execution.execute_statement.call_args.kwargs
    assert kwargs["statement"] == "SELECT * FROM t WHERE drawing_id = :drawing_id"
    assert "OR" not in kwargs["statement"]
    [p] = kwargs["parameters"]
    assert p.name == "drawing_id" and p.value == "x' OR '1'='1"
    assert kwargs["warehouse_id"] and kwargs["wait_timeout"].endswith("s")
    assert rows == [{"drawing_id": "BRL-PIP-ISO-0004", "fail_count": 2}]


def test_warehouse_failed_statement_is_unavailable(monkeypatch):
    ws = MagicMock()
    ws.statement_execution.execute_statement.return_value = _resp([], None, state="FAILED")
    monkeypatch.setattr(warehouse, "sp_workspace_client", lambda: ws)
    with pytest.raises(DataUnavailable):
        warehouse.query("SELECT 1")


def test_warehouse_sdk_exception_is_unavailable(monkeypatch):
    ws = MagicMock()
    ws.statement_execution.execute_statement.side_effect = ConnectionError("down")
    monkeypatch.setattr(warehouse, "sp_workspace_client", lambda: ws)
    with pytest.raises(DataUnavailable):
        warehouse.query("SELECT 1")


# --- lakebase --------------------------------------------------------------------------------------------------

def test_lakebase_query_uses_parameters_and_returns_dicts(monkeypatch):
    cur = MagicMock()
    cur.fetchall.return_value = [{"n": 1}]
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    pool = MagicMock()
    pool.connection.return_value.__enter__.return_value = conn
    monkeypatch.setattr(lakebase, "get_pool", lambda: pool)
    assert lakebase.query("SELECT %s", ("a",)) == [{"n": 1}]
    cur.execute.assert_called_once_with("SELECT %s", ("a",))


def test_lakebase_connection_error_is_unavailable(monkeypatch):
    import psycopg
    pool = MagicMock()
    pool.connection.side_effect = psycopg.OperationalError("boom with password=hunter2")
    monkeypatch.setattr(lakebase, "get_pool", lambda: pool)
    with pytest.raises(DataUnavailable) as e:
        lakebase.query("SELECT 1")
    assert "hunter2" not in str(e.value)


def test_lakebase_credential_generated_per_connection(monkeypatch):
    ws = MagicMock()
    ws.postgres.generate_database_credential.return_value = types.SimpleNamespace(token="tok-1")
    monkeypatch.setattr(lakebase, "sp_workspace_client", lambda: ws)
    monkeypatch.setenv("LAKEBASE_ENDPOINT", "projects/p/branches/b/endpoints/e")
    monkeypatch.setattr(lakebase, "config", types.SimpleNamespace(LAKEBASE_ENDPOINT="projects/p/branches/b/endpoints/e",
                                                                  LAKEBASE_DATABASE="db"))
    seen = {}

    def fake_connect(**kw):
        seen.update(kw)
        return "conn"

    monkeypatch.setenv("PGHOST", "h")
    monkeypatch.setenv("PGUSER", "sp-id")
    monkeypatch.setattr(lakebase.psycopg.Connection, "connect", staticmethod(fake_connect))
    assert lakebase._connect_with_fresh_credential() == "conn"
    ws.postgres.generate_database_credential.assert_called_once_with(endpoint="projects/p/branches/b/endpoints/e")
    assert seen["sslmode"] == "require" and seen["host"] == "h" and seen["user"] == "sp-id"
    assert seen["password"] == "tok-1"


# --- volume ----------------------------------------------------------------------------------------------------

def test_volume_open_pdf_streams_via_files_api(monkeypatch):
    ws = MagicMock()
    ws.files.download.return_value = types.SimpleNamespace(contents="STREAM")
    monkeypatch.setattr(volume, "sp_workspace_client", lambda: ws)
    assert volume.open_pdf("/Volumes/c/s/v/a.pdf") == "STREAM"
    ws.files.download.assert_called_once_with("/Volumes/c/s/v/a.pdf")


# --- vector search ---------------------------------------------------------------------------------------------

def test_vector_search_falls_back_to_sql_and_logs_once(monkeypatch, caplog):
    vector_search._reset_for_tests()
    ws = MagicMock()
    ws.vector_search_indexes.query_index.side_effect = PermissionError("no CAN_QUERY")
    monkeypatch.setattr(vector_search, "sp_workspace_client", lambda: ws)
    calls = []

    def fake_wh(sql, params=None):
        calls.append((sql, params))
        return [{"citation_id": "a", "citation_label": "L", "title": "t", "source": "s", "is_paraphrase": False,
                 "text": "x"}]

    monkeypatch.setattr(vector_search.warehouse, "query", fake_wh)
    with caplog.at_level(logging.INFO, logger="bluerridge"):
        assert vector_search.exact("L")["citation_label"] == "L"
        vector_search.exact("L")
        vector_search.related("L", "x", 3)
    assert vector_search.mode() == "sql_fallback"
    assert sum("vector_search fallback" in r.getMessage() for r in caplog.records) == 1
    assert all("L" not in sql.split("WHERE")[-1] or ":label" in sql for sql, _ in calls)
    assert calls[0][1] == {"label": "L"}


def test_vector_search_exact_uses_filter(monkeypatch):
    vector_search._reset_for_tests()
    ws = MagicMock()
    ws.vector_search_indexes.query_index.return_value = types.SimpleNamespace(
        manifest=types.SimpleNamespace(columns=[types.SimpleNamespace(name=n) for n in vector_search.COLUMNS]),
        result=types.SimpleNamespace(data_array=[["a", "L", "t", "s", "false", "x"]]))
    monkeypatch.setattr(vector_search, "sp_workspace_client", lambda: ws)
    row = vector_search.exact("L")
    kw = ws.vector_search_indexes.query_index.call_args.kwargs
    assert kw["index_name"] == "mfg_mc_se_sa.bluerridge_agents.code_excerpts_vs"
    assert '"citation_label": "L"' in kw["filters_json"] or kw["filters_json"] == '{"citation_label": "L"}'
    assert row["citation_label"] == "L" and vector_search.mode() == "vs"


# --- self-test -------------------------------------------------------------------------------------------------

SECRETISH = ("SECRET-ROW-CONTENT", "eyJ", "dapi", "Bearer", "tok-1")


def _patch_ok(monkeypatch):
    monkeypatch.setattr(selftest.lakebase, "query",
                        lambda sql, params=None: [{"n": 5, "payload": "SECRET-ROW-CONTENT"}])
    monkeypatch.setattr(selftest.warehouse, "query", lambda sql, params=None: [
        {"current_user": "sp-app-id", "n": "1200", "payload": "SECRET-ROW-CONTENT"}])
    monkeypatch.setattr(selftest.volume, "stat", lambda path: (True, 1234))
    monkeypatch.setattr(selftest.vector_search, "exact", lambda label: {"citation_label": label, "text": "SECRET-ROW-CONTENT"})
    monkeypatch.setattr(selftest.vector_search, "related", lambda label, text, k=3: [{"text": "SECRET-ROW-CONTENT"}] * 3)
    monkeypatch.setattr(selftest.vector_search, "mode", lambda: "vs")
    # Task 20 stages (route data functions, Genie as the SP) are covered in test_chat.py.
    monkeypatch.setattr(selftest, "run_routes", lambda: True, raising=False)
    monkeypatch.setattr(selftest, "run_genie", lambda: True, raising=False)


def test_selftest_logs_counts_only(monkeypatch, caplog):
    _patch_ok(monkeypatch)
    with caplog.at_level(logging.INFO, logger="bluerridge"):
        ok = selftest.run()
    assert ok is True
    msgs = [r.getMessage() for r in caplog.records if r.name.startswith("bluerridge")]
    text = "\n".join(msgs)
    for t in ("kpi_daily", "compliance_findings", "risk_forecast", "schedule_overdue", "daily_brief"):
        assert f"selftest lakebase {t}_synced rows=" in text
    assert "selftest warehouse current_user=sp-app-id drawing_register_visible=1200" in text
    assert "selftest volume " in text and "exists=True size=1234" in text
    assert "selftest vector_search mode=vs hits=" in text
    assert msgs[-1] == "selftest done ok=True"
    for bad in SECRETISH:
        assert bad not in text


def test_selftest_failure_logs_class_and_message_and_continues(monkeypatch, caplog):
    _patch_ok(monkeypatch)

    def boom(sql, params=None):
        raise DataUnavailable("Lakebase is unreachable")

    monkeypatch.setattr(selftest.lakebase, "query", boom)
    with caplog.at_level(logging.INFO, logger="bluerridge"):
        ok = selftest.run()
    assert ok is False
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert "selftest lakebase kpi_daily_synced FAILED DataUnavailable: Lakebase is unreachable" in text
    assert "selftest warehouse current_user=sp-app-id" in text      # later sources still ran
    assert "selftest done ok=False" in text
