"""/api/chat (Task 20): OBO-only Genie chat streamed as Server-Sent Events, plus the Genie layer, bbox parsing and the
extended startup self-test.

* Route tests mock the Genie layer (``genie.ask``) and Lakebase; the WorkspaceClient constructor in ``backend.auth`` is
  replaced by a recorder, so no network, no real token and no SDK auth are involved.
* Genie-layer tests drive ``genie.ask`` against canned payloads whose shapes were captured from the live Genie MCP
  server and the Conversation API (values replaced, ids fake).
"""
import json
import logging
import time
import types

import pytest
import requests
import urllib3
from backend import auth, genie, lakebase, selftest
from backend.errors import DataUnavailable
from backend.main import create_app
from backend.routes import chat, compliance
from databricks.sdk.service.dashboards import (
    GenieGetMessageQueryResultResponse,
    GenieMessage,
)
from fastapi.testclient import TestClient

FAKE_TOKEN = "FAKE-OBO-TOKEN-chat-do-not-leak-91b3"
OBO = {"x-forwarded-access-token": FAKE_TOKEN, "x-forwarded-email": "pm@example.com"}
CID = "0" * 31 + "1"
MID = "0" * 31 + "2"


# --- helpers / fixtures --------------------------------------------------------------------------------------------

def parse_sse(text: str) -> list[dict]:
    events = []
    for block in text.split("\n\n"):
        block = block.strip("\n")
        if not block:
            continue
        lines = block.split("\n")
        assert len(lines) == 1 and lines[0].startswith("data: "), f"not a one-line data event: {block!r}"
        events.append(json.loads(lines[0][len("data: "):]))
    return events


def types_of(events):
    return [e["type"] if e["type"] != "status" else f"status:{e['value']}" for e in events]


def jsonrpc_error(code, message="nope"):
    return {"jsonrpc": "2.0", "id": 1, "error": {"code": code, "message": message}}


def conn_refused():
    """What requests raises when the TCP connection cannot be opened (nothing was sent)."""
    reason = urllib3.exceptions.NewConnectionError(None, "Failed to establish a new connection: refused")
    return requests.ConnectionError(urllib3.exceptions.MaxRetryError(None, "/api/2.0/mcp/genie/space1", reason))


def conn_reset():
    """What requests raises when the connection drops after the request went out (Genie may have the question)."""
    return requests.ConnectionError(urllib3.exceptions.ProtocolError("Connection aborted.",
                                                                     ConnectionResetError(54, "reset by peer")))


class FakeWS:
    """Stands in for databricks.sdk.WorkspaceClient inside backend.auth; records how it was built.

    ``config`` lets the real Genie layer run against it: ``authenticate()`` returns the planted token as a header, the
    way the SDK would for a PAT client, so tests can prove that header never reaches an event or a log line.
    """
    built = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.config = types.SimpleNamespace(
            host="https://example.cloud.databricks.com",
            authenticate=lambda: {"Authorization": f"Bearer {kwargs.get('token')}"})
        self.genie = None
        FakeWS.built.append(self)


def turn(**kw) -> genie.GenieTurn:
    base = dict(transport="mcp", conversation_id=CID, message_id=MID, status="COMPLETED", text="", description="",
                sql=None, columns=[], rows=[], row_count=0, truncated=False, suggested=[])
    base.update(kw)
    return genie.GenieTurn(**base)


KNOWN = turn(
    text="**51** distinct drawings failed this week; most cite ASME B31.3 §322.",
    description="Count failed drawings",
    sql="SELECT drawing_id, citation FROM mfg_mc_se_sa.bluerridge_gold_pm.compliance_findings WHERE status = 'FAIL'",
    columns=["drawing_id", "citation"],
    rows=[["BRL-PIP-ISO-0004", "ASME B31.3 §322"], ["BRL-ELE-GA-0844", "OSHA 1910.147"],
          ["BRL-PIP-ISO-0004", "ASME B31.3 §322"]],
    row_count=3,
)

FAIL_ROWS = [
    {"drawing_id": "BRL-PIP-ISO-0004", "finding_id": "BRL-PIP-ISO-0004-C01", "page_num": 0,
     "bbox": "[0.1, 0.2, 0.3, 0.4]", "citation": "ASME B31.3 §322"},
]


class FakeGenie:
    def __init__(self, result=None, exc=None, sleep=0.0):
        self.result, self.exc, self.sleep = result, exc, sleep
        self.calls = []

    def __call__(self, w, message, conversation_id=None, **kw):
        self.calls.append({"w": w, "message": message, "conversation_id": conversation_id, **kw})
        cb = kw.get("on_conversation")
        if cb and self.result is not None and self.result.conversation_id:
            cb(self.result.conversation_id)
        if self.sleep:
            time.sleep(self.sleep)
        if self.exc:
            raise self.exc
        return self.result


class FakeLake:
    def __init__(self, rows=None, fail=False):
        self.rows = FAIL_ROWS if rows is None else rows
        self.fail = fail
        self.calls = []

    def __call__(self, sql, params=None):
        self.calls.append((sql, params))
        if self.fail:
            raise DataUnavailable("Lakebase is unreachable")
        return [dict(r) for r in self.rows if r["drawing_id"] in (params[1] if params else [])]


@pytest.fixture(autouse=True)
def _no_real_clients(monkeypatch):
    FakeWS.built = []
    monkeypatch.setattr(auth, "WorkspaceClient", FakeWS)
    sp_calls = []

    def no_sp():
        sp_calls.append(1)
        raise AssertionError("Genie in the chat must never run as the service principal")

    monkeypatch.setattr(auth, "sp_workspace_client", no_sp)
    return sp_calls


@pytest.fixture()
def client(tmp_path, monkeypatch):
    (tmp_path / "index.html").write_text("<html>SPA</html>")
    monkeypatch.setenv("BLUERRIDGE_SELFTEST", "off")
    return TestClient(create_app(static_dir=tmp_path), raise_server_exceptions=False)


@pytest.fixture()
def lake(monkeypatch):
    f = FakeLake()
    monkeypatch.setattr(lakebase, "query", f)
    return f


def use_genie(monkeypatch, **kw) -> FakeGenie:
    f = FakeGenie(**kw)
    monkeypatch.setattr(genie, "ask", f)
    return f


def post(client, message="How many drawings failed this week?", headers=OBO, **extra):
    return client.post("/api/chat", json={"message": message, **extra}, headers=headers)


# --- happy path ----------------------------------------------------------------------------------------------------

def test_chat_streams_sql_and_answer_for_known_question(client, lake, monkeypatch):
    use_genie(monkeypatch, result=KNOWN)
    r = post(client)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(r.text)
    assert types_of(events) == ["status:running", "conversation", "answer", "sql", "result", "sources", "status:done"]
    assert events[1]["conversation_id"] == CID
    assert events[2]["text"].startswith("**51** distinct drawings failed")
    assert events[3]["query"].startswith("SELECT drawing_id")
    res = events[4]
    assert res["columns"] == ["drawing_id", "citation"] and res["row_count"] == 3 and res["truncated"] is False
    assert len(res["rows"]) == 3


def test_sources_enriched_from_lakebase_fail_rows(client, lake, monkeypatch):
    use_genie(monkeypatch, result=KNOWN)
    events = parse_sse(post(client).text)
    items = next(e for e in events if e["type"] == "sources")["items"]
    drawings = [i for i in items if i["kind"] == "drawing"]
    # distinct ids in first-seen order; FAIL rows attach page/bbox/citation, a drawing without one stays clickable
    assert [d["drawing_id"] for d in drawings] == ["BRL-PIP-ISO-0004", "BRL-ELE-GA-0844"]
    assert drawings[0]["page_num"] == 0 and drawings[0]["bbox"] == [0.1, 0.2, 0.3, 0.4]
    assert drawings[0]["citation"] == "ASME B31.3 §322"
    assert drawings[1]["bbox"] is None and drawings[1]["page_num"] is None
    # one parameterized lookup: ids and status travel as parameters, never in the SQL text
    assert len(lake.calls) == 1
    sql, params = lake.calls[0]
    assert "compliance_findings_synced" in sql and "BRL-" not in sql and "%s" in sql
    assert params[0] == "FAIL" and params[1] == ["BRL-PIP-ISO-0004", "BRL-ELE-GA-0844"]
    cites = {i["label"]: i["url"] for i in items if i["kind"] == "citation"}
    assert cites == {"ASME B31.3 §322": "/api/citations/ASME%20B31.3%20%C2%A7322",
                     "OSHA 1910.147": "/api/citations/OSHA%201910.147"}


def test_sources_cap_ten_drawings_and_drop_malformed_ids(client, lake, monkeypatch):
    rows = [[f"BRL-PIP-ISO-{i:04d}"] for i in range(1, 16)] + [["x'); DROP TABLE t;--"]]
    use_genie(monkeypatch, result=turn(text="t", sql="SELECT 1", columns=["DRAWING_ID"], rows=rows, row_count=16))
    events = parse_sse(post(client).text)
    ids = lake.calls[0][1][1]
    assert len(ids) == 10 and all(i.startswith("BRL-PIP-ISO-") for i in ids)
    items = next(e for e in events if e["type"] == "sources")["items"]
    assert len([i for i in items if i["kind"] == "drawing"]) == 10


def test_citation_only_sources_from_answer_text_without_drawing_column(client, lake, monkeypatch):
    use_genie(monkeypatch, result=turn(text="See IBC 1005.1 and ASME B16.5 §4.2.", sql="SELECT 1", columns=["n"],
                                       rows=[[3]], row_count=1))
    events = parse_sse(post(client).text)
    items = next(e for e in events if e["type"] == "sources")["items"]
    assert [i["label"] for i in items] == ["ASME B16.5 §4.2", "IBC 1005.1"]
    assert lake.calls == []                      # no drawing_id column, no Lakebase lookup


def test_lakebase_down_still_finishes_with_bare_drawing_sources(client, monkeypatch):
    monkeypatch.setattr(lakebase, "query", FakeLake(fail=True))
    use_genie(monkeypatch, result=KNOWN)
    events = parse_sse(post(client).text)
    assert events[-1] == {"type": "status", "value": "done", "transport": "mcp"}
    items = next(e for e in events if e["type"] == "sources")["items"]
    assert {i["drawing_id"] for i in items if i["kind"] == "drawing"} == {"BRL-PIP-ISO-0004", "BRL-ELE-GA-0844"}


def test_follow_up_passes_conversation_id(client, lake, monkeypatch):
    g = use_genie(monkeypatch, result=KNOWN)
    post(client, message="and last week?", conversation_id=CID)
    assert g.calls[0]["conversation_id"] == CID and g.calls[0]["message"] == "and last week?"


# --- result shaping ------------------------------------------------------------------------------------------------

def test_slip_probability_column_is_stripped(client, lake, monkeypatch):
    use_genie(monkeypatch, result=turn(
        text="Top risks", sql="SELECT milestone_id, risk_band FROM risk_forecast",
        columns=["milestone_id", "slip_probability", "risk_band"],
        rows=[["MS-335", 0.91, "High"], ["MS-351", 0.88, "High"]], row_count=2))
    events = parse_sse(post(client).text)
    res = next(e for e in events if e["type"] == "result")
    assert res["columns"] == ["milestone_id", "risk_band"]
    assert res["rows"] == [["MS-335", "High"], ["MS-351", "High"]]
    assert "slip_probability" not in json.dumps(res) and "0.91" not in json.dumps(res)


@pytest.mark.parametrize("col", ["SLIP_PROBABILITY", "Slip_Probability", "max_slip_probability",
                                 "AVG_SLIP_PROBABILITY_PCT", "slip_probability_p90"])
def test_any_column_containing_slip_probability_is_stripped(client, lake, monkeypatch, col):
    use_genie(monkeypatch, result=turn(
        text="Top risks", sql="SELECT 1", columns=["milestone_id", col, "risk_band"],
        rows=[["MS-335", 0.91, "High"]], row_count=1))
    res = next(e for e in parse_sse(post(client).text) if e["type"] == "result")
    assert res["columns"] == ["milestone_id", "risk_band"] and res["rows"] == [["MS-335", "High"]]
    assert "slip_probability" not in json.dumps(res).lower() and "0.91" not in json.dumps(res)


def test_slip_days_column_is_not_stripped(client, lake, monkeypatch):
    use_genie(monkeypatch, result=turn(text="x", sql="SELECT 1", columns=["milestone_id", "projected_slip_days"],
                                       rows=[["MS-335", 12.5]], row_count=1))
    res = next(e for e in parse_sse(post(client).text) if e["type"] == "result")
    assert res["columns"] == ["milestone_id", "projected_slip_days"]


def test_result_capped_at_50_rows_with_truncated(client, lake, monkeypatch):
    rows = [[i] for i in range(60)]
    use_genie(monkeypatch, result=turn(text="many", sql="SELECT n", columns=["n"], rows=rows, row_count=60))
    res = next(e for e in parse_sse(post(client).text) if e["type"] == "result")
    assert len(res["rows"]) == 50 and res["row_count"] == 60 and res["truncated"] is True


def test_upstream_truncation_is_reported(client, lake, monkeypatch):
    use_genie(monkeypatch, result=turn(text="x", sql="SELECT n", columns=["n"], rows=[[1]], row_count=1,
                                       truncated=True))
    res = next(e for e in parse_sse(post(client).text) if e["type"] == "result")
    assert res["truncated"] is True


# --- empty / clarification -----------------------------------------------------------------------------------------

def test_chat_ambiguous_question_returns_graceful_empty(client, lake, monkeypatch):
    use_genie(monkeypatch, result=turn())
    events = parse_sse(post(client, message="which?").text)
    assert any(e["type"] == "answer" and "not sure" in e["text"].lower() for e in events)
    assert types_of(events) == ["status:running", "conversation", "answer", "status:done"]


def test_clarifying_question_is_relayed(client, lake, monkeypatch):
    q = "Which result do you want: failed piping ISO drawings, late milestones, or top risks?"
    use_genie(monkeypatch, result=turn(text=q, suggested=["Which milestones are late?"]))
    events = parse_sse(post(client, message="which?").text)
    answers = [e["text"] for e in events if e["type"] == "answer"]
    assert answers == [q]
    assert "sql" not in types_of(events) and events[-1]["value"] == "done"


# --- auth: OBO only ------------------------------------------------------------------------------------------------

def test_no_token_is_401_and_genie_never_called(client, monkeypatch, _no_real_clients):
    g = use_genie(monkeypatch, result=KNOWN)
    r = post(client, headers={"x-forwarded-email": "pm@example.com"})
    assert r.status_code == 401
    assert r.json()["error"] == "unauthorized"
    assert g.calls == [] and FakeWS.built == [] and _no_real_clients == []


def test_chat_uses_user_client_never_sp(client, lake, monkeypatch, _no_real_clients):
    g = use_genie(monkeypatch, result=KNOWN)
    assert post(client).status_code == 200
    assert len(FakeWS.built) == 1
    built = FakeWS.built[0]
    assert built.kwargs == {"token": FAKE_TOKEN, "auth_type": "pat"}
    assert g.calls[0]["w"] is built
    assert _no_real_clients == []                # sp_workspace_client() was never called


# --- validation ----------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("body", [{"message": ""}, {"message": "   \n "}, {"message": "x" * 2001}, {},
                                  {"message": 5}, {"message": "ok", "conversation_id": "../../etc"},
                                  {"message": "ok", "conversation_id": "x" * 65}])
def test_message_validation_422(client, monkeypatch, body):
    g = use_genie(monkeypatch, result=KNOWN)
    r = client.post("/api/chat", json=body, headers=OBO)
    assert r.status_code == 422
    assert set(r.json()) == {"error", "detail"}
    assert g.calls == []


def test_message_of_2000_chars_is_accepted(client, lake, monkeypatch):
    use_genie(monkeypatch, result=KNOWN)
    assert post(client, message="x" * 2000).status_code == 200


# --- errors / timeouts ---------------------------------------------------------------------------------------------

def test_route_wall_clock_timeout_is_error_event(client, lake, monkeypatch):
    monkeypatch.setattr(chat, "CHAT_TIMEOUT_S", 0.3)
    use_genie(monkeypatch, result=KNOWN, sleep=1.5)
    r = post(client)
    events = parse_sse(r.text)
    assert events[0] == {"type": "status", "value": "running"}
    last = events[-1]
    assert last["type"] == "status" and last["value"] == "error" and "seconds" in last["message"]
    assert "Traceback" not in r.text and 'File "' not in r.text


def test_genie_timeout_is_error_event(client, lake, monkeypatch):
    use_genie(monkeypatch, exc=genie.GenieTimeout())
    events = parse_sse(post(client).text)
    assert events[-1]["value"] == "error" and "seconds" in events[-1]["message"]


def test_genie_error_safe_message(client, lake, monkeypatch):
    use_genie(monkeypatch, exc=genie.GenieError("forbidden"))
    events = parse_sse(post(client).text)
    assert events[-1]["value"] == "error"
    assert events[-1]["message"] == genie.SAFE_MESSAGES["forbidden"]


def test_unexpected_exception_is_generic_error_without_details(client, lake, monkeypatch, caplog):
    use_genie(monkeypatch, exc=RuntimeError("secret internal detail /srv/app/genie.py line 9"))
    with caplog.at_level(logging.DEBUG):
        r = post(client)
    events = parse_sse(r.text)
    assert events[-1]["value"] == "error"
    assert "secret internal detail" not in r.text and "Traceback" not in r.text
    assert "secret internal detail" not in caplog.text


def test_heartbeat_repeats_running_while_waiting(client, lake, monkeypatch):
    monkeypatch.setattr(chat, "HEARTBEAT_S", 0.1)
    use_genie(monkeypatch, result=KNOWN, sleep=0.45)
    events = parse_sse(post(client).text)
    t = types_of(events)
    assert t.count("status:running") >= 2 and t[-1] == "status:done"
    assert t.index("answer") > max(i for i, x in enumerate(t) if x == "status:running")


# --- token hygiene -------------------------------------------------------------------------------------------------

def test_planted_token_never_in_events_headers_or_logs(client, lake, monkeypatch, caplog):
    for result, exc in ((KNOWN, None), (None, genie.GenieError("unavailable")), (None, RuntimeError(FAKE_TOKEN))):
        use_genie(monkeypatch, result=result, exc=exc)
        with caplog.at_level(logging.DEBUG):
            r = post(client)
        assert FAKE_TOKEN not in r.text
        assert all(FAKE_TOKEN not in v for v in r.headers.values())
    assert FAKE_TOKEN not in caplog.text


@pytest.mark.parametrize("response", [
    (502, {"message": f"bad gateway for Bearer {FAKE_TOKEN}"}),                     # 5xx branch
    (500, f"upstream said {FAKE_TOKEN}"),
    requests.ConnectionError(f"reset by peer while sending Authorization: Bearer {FAKE_TOKEN}"),  # RequestException
    conn_reset(), conn_refused(),
    (200, {"jsonrpc": "2.0", "id": 1, "error": f"denied {FAKE_TOKEN}"}),
    RuntimeError(f"unexpected {FAKE_TOKEN}")])
def test_planted_token_never_leaks_through_the_real_genie_layer(client, lake, monkeypatch, caplog, response):
    srv = McpServer([response])
    monkeypatch.setattr(genie, "_post", srv)
    monkeypatch.setattr(genie, "_conv_ask", lambda *a, **k: (_ for _ in ()).throw(genie.GenieError("unavailable")))
    with caplog.at_level(logging.DEBUG):
        r = post(client)
    events = parse_sse(r.text)
    assert events[-1]["value"] == "error"
    assert srv.requests[0]["headers"]["Authorization"] == f"Bearer {FAKE_TOKEN}"   # the header really was there
    assert FAKE_TOKEN not in r.text and FAKE_TOKEN not in json.dumps(events)
    assert all(FAKE_TOKEN not in v for v in r.headers.values())
    assert FAKE_TOKEN not in caplog.text


# --- transport reported in the stream ------------------------------------------------------------------------------

@pytest.mark.parametrize("transport", ["mcp", "conversation_api"])
def test_done_event_carries_transport(client, lake, monkeypatch, transport):
    use_genie(monkeypatch, result=turn(transport=transport, text="ok"))
    events = parse_sse(post(client).text)
    assert events[-1] == {"type": "status", "value": "done", "transport": transport}


def test_error_event_carries_transport_when_known(client, lake, monkeypatch):
    err = genie.GenieError("forbidden")
    err.transport = "conversation_api"
    use_genie(monkeypatch, exc=err)
    last = parse_sse(post(client).text)[-1]
    assert last == {"type": "status", "value": "error", "message": genie.SAFE_MESSAGES["forbidden"],
                    "transport": "conversation_api"}


def test_error_event_without_known_transport_has_no_transport_key(client, lake, monkeypatch):
    use_genie(monkeypatch, exc=RuntimeError("x"))
    assert "transport" not in parse_sse(post(client).text)[-1]
    monkeypatch.setattr(chat, "CHAT_TIMEOUT_S", 0.2)
    use_genie(monkeypatch, result=KNOWN, sleep=0.8)
    assert "transport" not in parse_sse(post(client).text)[-1]


def test_route_fallback_runs_with_the_same_user_client(client, lake, monkeypatch, _no_real_clients):
    monkeypatch.setattr(genie, "_post", McpServer([(403, None)]))
    called = []
    monkeypatch.setattr(genie, "_conv_ask", conv_recorder(called))
    events = parse_sse(post(client).text)
    assert len(FakeWS.built) == 1 and called[0][0] is FakeWS.built[0]
    assert FakeWS.built[0].kwargs == {"token": FAKE_TOKEN, "auth_type": "pat"}
    assert events[-1] == {"type": "status", "value": "done", "transport": "conversation_api"}
    assert _no_real_clients == []


def test_route_mcp_error_event_reports_mcp(client, lake, monkeypatch):
    monkeypatch.setattr(genie, "_post", McpServer([(502, None)]))
    monkeypatch.setattr(genie, "_conv_ask", no_fallback)
    last = parse_sse(post(client).text)[-1]
    assert last["value"] == "error" and last["transport"] == "mcp"
    assert last["message"] == genie.SAFE_MESSAGES["unavailable"]


def test_mcp_layer_never_leaks_token(monkeypatch, caplog):
    w = mcp_ws(FAKE_TOKEN)
    monkeypatch.setattr(genie, "_post", lambda url, headers, payload, timeout: (403, {"error": f"denied {FAKE_TOKEN}"}))
    monkeypatch.setattr(genie, "_conv_ask", lambda *a, **k: (_ for _ in ()).throw(genie.GenieError("forbidden")))
    with caplog.at_level(logging.DEBUG), pytest.raises(genie.GenieError) as ei:
        genie.ask(w, "q", space_id="space1")
    assert FAKE_TOKEN not in str(ei.value) and FAKE_TOKEN not in caplog.text


# --- Genie layer: MCP transport (payload shapes from the live server) ----------------------------------------------

def mcp_ws(token="tok"):
    cfg = types.SimpleNamespace(host="https://example.cloud.databricks.com",
                                authenticate=lambda: {"Authorization": f"Bearer {token}"})
    return types.SimpleNamespace(config=cfg, genie=None)


def mcp_body(status, content=None, cid=CID, mid=MID):
    sc = {"content": content or {}, "conversationId": cid, "messageId": mid, "status": status}
    return {"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": json.dumps(sc)}],
                                                  "isError": False, "structuredContent": sc}}


MCP_CONTENT = {
    "queryAttachments": [{
        "query": "SELECT COUNT(DISTINCT `drawing_id`) AS `drawings_failed` FROM x WHERE `status` = 'FAIL'",
        "description": "You want to know how many unique drawings failed.",
        "statement_response": {
            "statement_id": "s-1", "status": {"state": "SUCCEEDED"},
            "manifest": {"format": "JSON_ARRAY", "schema": {"column_count": 3, "columns": [
                {"name": "drawings_failed", "type_name": "LONG", "position": 0},
                {"name": "share", "type_name": "DOUBLE", "position": 1},
                {"name": "note", "type_name": "STRING", "position": 2}]},
                "total_row_count": 1, "truncated": False},
            "result": {"row_count": 1, "data_array": [
                {"values": [{"string_value": "51"}, {"string_value": "0.21"}, {"null_value": "NULL_VALUE"}]}]}},
    }],
    "textAttachments": ["**51** distinct drawings failed this week."],
    "suggestedQuestions": ["Which disciplines failed most?"],
}


class McpServer:
    """Fake JSON-RPC endpoint: a scripted list of (status, body) responses or exceptions to raise; records every
    request. JSON-RPC bodies echo the request id (as the live server does) unless ``echo_id=False``."""

    def __init__(self, responses, repeat_last=False, echo_id=True):
        self.responses = list(responses)
        self.repeat_last, self.echo_id = repeat_last, echo_id
        self.requests = []

    def __call__(self, url, headers, payload, timeout):
        self.requests.append({"url": url, "headers": headers, "payload": payload, "timeout": timeout})
        r = self.responses[0] if (self.repeat_last and len(self.responses) == 1) else self.responses.pop(0)
        if isinstance(r, BaseException):
            raise r
        status, body = r
        if self.echo_id and isinstance(body, dict) and "jsonrpc" in body:
            body = {**body, "id": payload["id"]}
        return status, body


def conv_recorder(called, transport="conversation_api"):
    def fake_conv(w, space_id, message, conversation_id, deadline, on_conversation):
        called.append((w, space_id, message, conversation_id))
        return turn(transport=transport, text="ok")
    return fake_conv


def no_fallback(*a, **k):
    pytest.fail("must not fall back to the Conversation API")


def test_mcp_query_then_poll_until_completed(monkeypatch):
    monkeypatch.setattr(genie, "POLL_INTERVAL_S", 0.01)
    srv = McpServer([(200, mcp_body("EXECUTING_QUERY")), (200, mcp_body("ASKING_AI")),
                     (200, mcp_body("COMPLETED", MCP_CONTENT))])
    monkeypatch.setattr(genie, "_post", srv)
    seen = []
    t = genie.ask(mcp_ws(), "How many drawings failed this week?", space_id="space1", on_conversation=seen.append)
    first, second = srv.requests[0], srv.requests[1]
    assert first["url"] == "https://example.cloud.databricks.com/api/2.0/mcp/genie/space1"
    assert first["payload"]["method"] == "tools/call"
    assert first["payload"]["params"] == {"name": "query_space_space1",
                                          "arguments": {"query": "How many drawings failed this week?"}}
    assert second["payload"]["params"] == {"name": "poll_response_space1",
                                           "arguments": {"conversation_id": CID, "message_id": MID}}
    assert first["headers"]["Authorization"] == "Bearer tok"
    assert seen == [CID]
    assert t.transport == "mcp" and t.status == "COMPLETED" and t.conversation_id == CID
    assert t.text == "**51** distinct drawings failed this week."
    assert t.sql.startswith("SELECT COUNT(DISTINCT")
    assert t.columns == ["drawings_failed", "share", "note"]
    assert t.rows == [[51, 0.21, None]] and t.row_count == 1 and t.truncated is False
    assert t.suggested == ["Which disciplines failed most?"]
    assert t.headline() == 51


def test_mcp_follow_up_sends_conversation_id(monkeypatch):
    srv = McpServer([(200, mcp_body("COMPLETED", MCP_CONTENT))])
    monkeypatch.setattr(genie, "_post", srv)
    genie.ask(mcp_ws(), "and by discipline?", CID, space_id="space1")
    assert srv.requests[0]["payload"]["params"]["arguments"] == {"query": "and by discipline?", "conversation_id": CID}


def test_mcp_plain_list_rows_and_text_only_payload(monkeypatch):
    content = {"textAttachments": ["Which milestones do you mean?"], "suggestedQuestions": []}
    monkeypatch.setattr(genie, "_post", McpServer([(200, mcp_body("COMPLETED", content))]))
    t = genie.ask(mcp_ws(), "which?", space_id="space1")
    assert t.sql is None and t.rows == [] and t.text == "Which milestones do you mean?"
    assert genie._cells({"values": [{"bool_value": True}, {"number_value": 2.5}, {}]}) == [True, 2.5, None]
    assert genie._cells(["a", None]) == ["a", None]


def test_mcp_deadline_raises_timeout(monkeypatch):
    monkeypatch.setattr(genie, "POLL_INTERVAL_S", 0.01)
    monkeypatch.setattr(genie, "_post", McpServer([(200, mcp_body("EXECUTING_QUERY"))], repeat_last=True))
    monkeypatch.setattr(genie, "_conv_ask", no_fallback)
    with pytest.raises(genie.GenieTimeout) as ei:
        genie.ask(mcp_ws(), "q", space_id="space1", deadline_s=0.2)
    assert ei.value.transport == "mcp"


def test_mcp_failed_status_is_genie_error(monkeypatch):
    monkeypatch.setattr(genie, "_post", McpServer([(200, mcp_body("FAILED"))]))
    with pytest.raises(genie.GenieError) as ei:
        genie.ask(mcp_ws(), "q", space_id="space1")
    assert ei.value.kind == "failed"


def test_mcp_401_is_not_retried_on_another_transport(monkeypatch):
    monkeypatch.setattr(genie, "_post", McpServer([(401, {"error": "x"})]))
    monkeypatch.setattr(genie, "_conv_ask", lambda *a, **k: pytest.fail("no fallback on 401"))
    with pytest.raises(genie.GenieError) as ei:
        genie.ask(mcp_ws(), "q", space_id="space1")
    assert ei.value.kind == "unauthenticated"


# Refusals that happen before Genie can have received the question: the only cases that may fall back.
@pytest.mark.parametrize("response", [
    (403, {"error_code": "PERMISSION_DENIED"}), (404, None), (400, {"error": "bad request"}), (405, None),
    (406, {"error": "Not Acceptable: client must accept text/event-stream"}), (415, None),
    (200, jsonrpc_error(-32601)), (200, jsonrpc_error(-32600, "session not initialized")),
    (200, jsonrpc_error(-32602)), (200, jsonrpc_error(-32700)),
    requests.ConnectTimeout("connect timed out"), conn_refused()])
def test_mcp_refused_before_send_falls_back_with_same_client(monkeypatch, response, caplog):
    monkeypatch.setattr(genie, "_post", McpServer([response]))
    called = []
    monkeypatch.setattr(genie, "_conv_ask", conv_recorder(called))
    w = mcp_ws()
    with caplog.at_level(logging.WARNING, logger="bluerridge"):
        t = genie.ask(w, "q", space_id="space1")
    assert t.transport == "conversation_api"
    assert len(called) == 1 and called[0][0] is w and called[0][1:] == ("space1", "q", None)
    assert "falling back to conversation_api" in caplog.text


# Failures after the request may have reached Genie: falling back could ask the question twice, so never.
@pytest.mark.parametrize("response,kind", [
    ((500, None), "unavailable"), ((502, {"message": "bad gateway"}), "unavailable"), ((504, None), "unavailable"),
    ((429, None), "unavailable"), ((200, None), "unavailable"), ((200, "not json-rpc"), "unavailable"),
    ((200, jsonrpc_error(-32603, "internal error")), "protocol"), ((200, jsonrpc_error(-32000)), "protocol"),
    (conn_reset(), "unavailable")])
def test_mcp_first_call_never_falls_back_once_genie_may_have_the_question(monkeypatch, response, kind):
    monkeypatch.setattr(genie, "_post", McpServer([response]))
    monkeypatch.setattr(genie, "_conv_ask", no_fallback)
    with pytest.raises(genie.GenieError) as ei:
        genie.ask(mcp_ws(), "q", space_id="space1")
    assert ei.value.kind == kind and ei.value.transport == "mcp"
    assert not isinstance(ei.value, genie.GenieTimeout)


@pytest.mark.parametrize("exc", [requests.ReadTimeout("read timed out"), requests.Timeout("timed out")])
def test_mcp_first_call_read_timeout_is_timeout_without_fallback(monkeypatch, exc):
    monkeypatch.setattr(genie, "_post", McpServer([exc]))
    monkeypatch.setattr(genie, "_conv_ask", no_fallback)
    with pytest.raises(genie.GenieTimeout):
        genie.ask(mcp_ws(), "q", space_id="space1")


@pytest.mark.parametrize("poll_response", [(403, None), (404, None), (406, None), (502, None), (500, None),
                                           (200, jsonrpc_error(-32601)), conn_refused(), conn_reset()])
def test_mcp_poll_errors_never_fall_back(monkeypatch, poll_response):
    monkeypatch.setattr(genie, "POLL_INTERVAL_S", 0.01)
    monkeypatch.setattr(genie, "_post", McpServer([(200, mcp_body("EXECUTING_QUERY")), poll_response]))
    monkeypatch.setattr(genie, "_conv_ask", no_fallback)
    with pytest.raises(genie.GenieError) as ei:
        genie.ask(mcp_ws(), "q", space_id="space1")
    assert ei.value.transport == "mcp"


@pytest.mark.parametrize("err", ["boom", ["a"], 42, {}, True])
def test_mcp_non_object_jsonrpc_error_is_safe_protocol_error(monkeypatch, err, caplog):
    monkeypatch.setattr(genie, "_post", McpServer([(200, {"jsonrpc": "2.0", "id": 1, "error": err})]))
    monkeypatch.setattr(genie, "_conv_ask", no_fallback)
    with caplog.at_level(logging.WARNING, logger="bluerridge"), pytest.raises(genie.GenieError) as ei:
        genie.ask(mcp_ws(), "q", space_id="space1")
    assert ei.value.kind == "protocol" and str(ei.value) == genie.SAFE_MESSAGES["protocol"]
    assert "boom" not in caplog.text


def test_mcp_response_id_mismatch_is_protocol_error(monkeypatch):
    srv = McpServer([(200, {**mcp_body("COMPLETED", MCP_CONTENT), "id": "someone-else"})], echo_id=False)
    monkeypatch.setattr(genie, "_post", srv)
    monkeypatch.setattr(genie, "_conv_ask", no_fallback)
    with pytest.raises(genie.GenieError) as ei:
        genie.ask(mcp_ws(), "q", space_id="space1")
    assert ei.value.kind == "protocol"


def test_mcp_response_without_id_is_accepted(monkeypatch):
    body = {k: v for k, v in mcp_body("COMPLETED", MCP_CONTENT).items() if k != "id"}
    monkeypatch.setattr(genie, "_post", McpServer([(200, body)], echo_id=False))
    assert genie.ask(mcp_ws(), "q", space_id="space1").headline() == 51


def test_errors_after_fallback_carry_conversation_api_transport(monkeypatch):
    monkeypatch.setattr(genie, "_post", McpServer([(403, None)]))
    api = FakeGenieAPI(statuses=("FAILED",))
    w = types.SimpleNamespace(config=mcp_ws().config, genie=api)
    with pytest.raises(genie.GenieError) as ei:
        genie.ask(w, "q", space_id="space1")
    assert ei.value.kind == "failed" and ei.value.transport == "conversation_api"
    assert api.calls[0] == ("start", "space1", "q")


# --- Genie layer: silent-parse cases (key names only in the log) ---------------------------------------------------

SQL_TEXT = "SELECT COUNT(DISTINCT drawing_id) AS drawings_failed FROM secret_table_name"


def test_mcp_sql_without_statement_response_warns_and_fetches_rows(monkeypatch, caplog):
    content = {"queryAttachments": [{"query": SQL_TEXT, "description": "VALUE-DESC"}],
               "textAttachments": ["VALUE-TEXT 51"]}
    monkeypatch.setattr(genie, "_post", McpServer([(200, mcp_body("COMPLETED", content))]))
    api = FakeGenieAPI(statuses=("COMPLETED",))
    w = types.SimpleNamespace(config=mcp_ws().config, genie=api)
    with caplog.at_level(logging.WARNING, logger="bluerridge"):
        t = genie.ask(w, "q", space_id="space1")
    assert t.transport == "mcp" and t.sql == SQL_TEXT
    assert t.columns == ["drawings_failed"] and t.rows == [[51]] and t.headline() == 51
    assert ("get", CID, MID) in api.calls and ("result", "att-q") in api.calls
    warning = caplog.text
    assert "statement_response" in warning and "description" in warning and "query" in warning
    for value in ("secret_table_name", "VALUE-DESC", "VALUE-TEXT"):
        assert value not in warning


def test_mcp_result_fetch_failure_keeps_answer_and_logs_class_only(monkeypatch, caplog):
    content = {"queryAttachments": [{"query": SQL_TEXT}], "textAttachments": ["Fifty-one."]}
    monkeypatch.setattr(genie, "_post", McpServer([(200, mcp_body("COMPLETED", content))]))

    class Broken:
        def get_message(self, *a):
            raise RuntimeError("secret_table_name is gone")

    w = types.SimpleNamespace(config=mcp_ws().config, genie=Broken())
    with caplog.at_level(logging.WARNING, logger="bluerridge"):
        t = genie.ask(w, "q", space_id="space1")
    assert t.text == "Fifty-one." and t.sql == SQL_TEXT and t.rows == [] and t.columns == []
    assert "RuntimeError" in caplog.text and "secret_table_name" not in caplog.text


def test_mcp_nothing_parsed_warns_with_key_names_only(monkeypatch, caplog):
    content = {"unexpectedAttachments": ["VALUE-X"], "otherThing": {"k": "VALUE-Y"}}
    monkeypatch.setattr(genie, "_post", McpServer([(200, mcp_body("COMPLETED", content))]))
    with caplog.at_level(logging.WARNING, logger="bluerridge"):
        t = genie.ask(mcp_ws(), "q", space_id="space1")
    assert not (t.text or t.sql or t.rows)
    assert "nothing parsed" in caplog.text and "unexpectedAttachments" in caplog.text
    assert "VALUE-X" not in caplog.text and "VALUE-Y" not in caplog.text


def test_mcp_normal_answer_logs_no_parse_warning(monkeypatch, caplog):
    monkeypatch.setattr(genie, "_post", McpServer([(200, mcp_body("COMPLETED", MCP_CONTENT))]))
    with caplog.at_level(logging.WARNING, logger="bluerridge"):
        genie.ask(mcp_ws(), "q", space_id="space1")
    assert caplog.records == []


def test_conversation_api_nothing_parsed_warns_with_key_names_only(monkeypatch, caplog):
    class Empty(FakeGenieAPI):
        def get_message(self, space_id, conversation_id, message_id):
            return GenieMessage.from_dict({"conversation_id": CID, "message_id": MID, "status": "COMPLETED",
                                           "content": "VALUE-QUESTION", "attachments": []})

    w = types.SimpleNamespace(genie=Empty(), config=None)
    with caplog.at_level(logging.WARNING, logger="bluerridge"):
        t = genie.ask(w, "q", space_id="space1", transport="conversation_api")
    assert not (t.text or t.sql or t.rows)
    assert "nothing parsed" in caplog.text and "VALUE-QUESTION" not in caplog.text


def test_transport_env_selects_conversation_api(monkeypatch):
    monkeypatch.setenv("GENIE_TRANSPORT", "conversation_api")
    monkeypatch.setattr(genie, "_post", lambda *a, **k: pytest.fail("MCP must not be called"))
    monkeypatch.setattr(genie, "_conv_ask", lambda w, s, m, c, d, cb: turn(transport="conversation_api"))
    assert genie.ask(mcp_ws(), "q", space_id="space1").transport == "conversation_api"


# --- Genie layer: Conversation API transport (real SDK dataclasses, shapes from the CLI) ---------------------------

CONV_MESSAGE = {
    "conversation_id": CID, "message_id": MID, "id": MID, "status": "COMPLETED",
    "content": "How many drawings failed this week?",
    "attachments": [
        {"attachment_id": "att-q", "query": {"description": "Count failed drawings", "statement_id": "s-2",
                                              "query": "SELECT COUNT(DISTINCT drawing_id) AS drawings_failed FROM x",
                                              "query_result_metadata": {"row_count": 1}}},
        {"attachment_id": "att-s", "suggested_questions": {"questions": ["By discipline?"]}},
        {"text": {"content": "**51** distinct drawings failed this week.",
                  "purpose": "TEXT_ATTACHMENT_PURPOSE_ANSWER"}},
    ],
}
CONV_RESULT = {"statement_response": {
    "manifest": {"schema": {"column_count": 1, "columns": [{"name": "drawings_failed", "type_name": "LONG"}]},
                 "total_row_count": 1, "truncated": False},
    "result": {"data_array": [["51"]], "row_count": 1}}}


class FakeGenieAPI:
    def __init__(self, statuses=("EXECUTING_QUERY", "COMPLETED")):
        self.statuses = list(statuses)
        self.calls = []

    def start_conversation(self, space_id, content):
        self.calls.append(("start", space_id, content))
        return types.SimpleNamespace(conversation_id=CID, message_id=MID)

    def create_message(self, space_id, conversation_id, content):
        self.calls.append(("create", space_id, conversation_id, content))
        return types.SimpleNamespace(conversation_id=conversation_id, message_id=MID)

    def get_message(self, space_id, conversation_id, message_id):
        self.calls.append(("get", conversation_id, message_id))
        status = self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]
        return GenieMessage.from_dict({**CONV_MESSAGE, "status": status})

    def get_message_attachment_query_result(self, space_id, conversation_id, message_id, attachment_id):
        self.calls.append(("result", attachment_id))
        return GenieGetMessageQueryResultResponse.from_dict(CONV_RESULT)


def test_conversation_api_transport(monkeypatch):
    monkeypatch.setattr(genie, "POLL_INTERVAL_S", 0.01)
    api = FakeGenieAPI()
    w = types.SimpleNamespace(genie=api, config=None)
    seen = []
    t = genie.ask(w, "How many drawings failed this week?", space_id="space1", transport="conversation_api",
                  on_conversation=seen.append)
    assert api.calls[0] == ("start", "space1", "How many drawings failed this week?")
    assert ("result", "att-q") in api.calls and seen == [CID]
    assert t.transport == "conversation_api" and t.text == "**51** distinct drawings failed this week."
    assert t.sql.startswith("SELECT COUNT") and t.columns == ["drawings_failed"] and t.rows == [[51]]
    assert t.suggested == ["By discipline?"] and t.headline() == 51


def test_conversation_api_follow_up_uses_create_message(monkeypatch):
    api = FakeGenieAPI(statuses=("COMPLETED",))
    genie.ask(types.SimpleNamespace(genie=api, config=None), "and last week?", CID, space_id="space1",
              transport="conversation_api")
    assert api.calls[0] == ("create", "space1", CID, "and last week?")


# --- bbox parsing (T19 fix folded into T20) ------------------------------------------------------------------------

@pytest.fixture()
def fresh_bbox_warning():
    compliance._reset_bbox_warning()
    yield
    compliance._reset_bbox_warning()


@pytest.mark.parametrize("raw", [[0.1, 0.2, 0.3, 0.4], ["0.1", "0.2", "0.3", "0.4"], (0.1, 0.2, 0.3, 0.4),
                                 "[0.1, 0.2, 0.3, 0.4]", " [0.1,0.2,0.3,0.4] ", "{0.1,0.2,0.3,0.4}"])
def test_bbox_parses_list_json_and_pg_literal(raw, fresh_bbox_warning, caplog):
    with caplog.at_level(logging.WARNING):
        assert compliance._bbox(raw) == [0.1, 0.2, 0.3, 0.4]
    assert caplog.records == []


def test_bbox_none_is_none_without_warning(fresh_bbox_warning, caplog):
    with caplog.at_level(logging.WARNING):
        assert compliance._bbox(None) is None
    assert caplog.records == []


@pytest.mark.parametrize("raw", ["not a box", "[0.1, 0.2, 0.3]", [1, 2, 3, 4, 5], [0.1, "x", 0.3, 0.4], {"a": 1},
                                 "{NULL,0.2,0.3,0.4}", "[NaN, 0.2, 0.3, 0.4]", 7])
def test_bbox_unparseable_is_none_and_warns_once(raw, fresh_bbox_warning, caplog):
    with caplog.at_level(logging.WARNING):
        assert compliance._bbox(raw) is None
        assert compliance._bbox(raw) is None
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1 and "bbox" in warnings[0].getMessage()


# --- extended startup self-test ------------------------------------------------------------------------------------

SECRET = "SECRET-ROW-CONTENT"


class SelftestLake:
    """Answers the route SQL with counts shaped like production, plus planted row content that must not be logged."""

    def __call__(self, sql, params=None):
        s = " ".join(sql.split())
        if "pg_typeof(bbox)" in s:
            return [{"bbox": "[0.1, 0.2, 0.3, 0.4]", "pg_type": "jsonb"}]
        if "GROUP BY drawing_id" in s:
            return [{"status": "PASS", "n": 187}, {"status": "FAIL", "n": 51}]
        if "GROUP BY citation" in s:
            return [{"citation": SECRET, "fails": 30}]
        if "count(*) AS total" in s:
            return [{"total": 77}]
        if "compliance_findings_synced" in s:
            return [{"drawing_id": "BRL-PIP-ISO-0004", "finding_id": "F-1", "status": "FAIL", "severity": "high",
                     "citation": SECRET, "reason": SECRET, "evidence_text": SECRET, "page_num": 0,
                     "bbox": "[0.1, 0.2, 0.3, 0.4]", "bbox_source": "gt", "review_date": "2026-11-05"}]
        if "GROUP BY risk_band" in s:
            return [{"risk_band": "High", "n": 26}, {"risk_band": "Medium", "n": 20}, {"risk_band": "Low", "n": 18}]
        if "risk_forecast_synced" in s:
            keys = [k.strip() for k in ["milestone_id", " name", " discipline", " criticality", " planned_end", " risk_band", " risk_rank", " projected_slip_days", " forecast_confidence_lower", " forecast_confidence_upper", " upstream_delay_days", " upstream_milestone_id"]]
            return [{k: SECRET for k in keys} for _ in range(5)]
        if "schedule_overdue_synced" in s:
            return [{"milestone_id": SECRET, "name": SECRET, "discipline": "p", "criticality": "h",
                     "planned_end": "2026-11-01", "days_late": d, "downstream_open_count": 0}
                    for d in (15, 9, 7, 5, 3, 2, 0)]
        if "kpi_daily_synced" in s:
            return [{k: SECRET for k in (
                "project_id", "snapshot_date", "schedule_status", "milestones_hit", "milestones_total",
                "slipped_milestone_id", "slipped_days", "budget_total_usd", "budget_overrun_usd", "budget_eac_pct",
                "safety_days_without_incident", "recordables_28d", "trir_28d", "open_ncrs", "open_ncrs_compliance",
                "open_ncrs_workmanship", "compliance_reviewed_week", "compliance_passed_week",
                "compliance_failed_week")}]
        if "daily_brief_synced" in s:
            return [{"brief_md": SECRET, "brief_date": "2026-11-06", "validation_status": "PASSED",
                     "prompt_version": "v3", "generated_at": "x"}]
        raise AssertionError(f"unexpected SQL: {s}")


def _log_text(caplog):
    return "\n".join(r.getMessage() for r in caplog.records if r.name.startswith("bluerridge"))


def test_selftest_route_lines_counts_and_bbox_shape(monkeypatch, caplog, fresh_bbox_warning):
    monkeypatch.setattr(lakebase, "query", SelftestLake())
    with caplog.at_level(logging.INFO, logger="bluerridge"):
        ok = selftest.run_routes()
    text = _log_text(caplog)
    assert ok is True
    assert "selftest route compliance_summary reviewed=238 failed=51" in text
    assert ("selftest route compliance_findings total=77 bbox_raw_type=str bbox_pg_type=jsonb "
            "bbox_type=list bbox_len=4 bbox_floats=True") in text
    assert "selftest route risk_top n=5 high=26" in text
    assert "selftest route overdue late=6 due_today=1" in text
    assert "selftest route kpi_today ok=True" in text
    assert "selftest route brief_today ok=True" in text
    assert SECRET not in text


def test_selftest_genie_as_sp_same_transport_counts_only(monkeypatch, caplog):
    sp = object()
    monkeypatch.setattr(selftest, "sp_workspace_client", lambda: sp)
    g = FakeGenie(result=turn(text=SECRET, sql=f"SELECT '{SECRET}'", columns=["drawings_failed"], rows=[[51]],
                              row_count=1))
    monkeypatch.setattr(genie, "ask", g)
    with caplog.at_level(logging.INFO, logger="bluerridge"):
        ok = selftest.run_genie()
    text = _log_text(caplog)
    assert ok is True and g.calls[0]["w"] is sp and g.calls[0]["message"] == "How many drawings failed this week?"
    assert "selftest genie transport=mcp status=COMPLETED got_sql=True rows=1 headline=51" in text
    assert SECRET not in text


def test_selftest_genie_failure_logs_class_and_continues(monkeypatch, caplog):
    monkeypatch.setattr(selftest, "sp_workspace_client", lambda: object())
    monkeypatch.setattr(genie, "ask", FakeGenie(exc=genie.GenieError("forbidden")))
    with caplog.at_level(logging.INFO, logger="bluerridge"):
        assert selftest.run_genie() is False
    assert "selftest genie FAILED GenieError kind=forbidden" in _log_text(caplog)


def test_selftest_run_includes_routes_and_genie(monkeypatch, caplog):
    order = []
    monkeypatch.setattr(selftest, "run_sources", lambda: order.append("sources") or True)
    monkeypatch.setattr(selftest, "run_routes", lambda: order.append("routes") or True)
    monkeypatch.setattr(selftest, "run_genie", lambda: order.append("genie") or False)
    with caplog.at_level(logging.INFO, logger="bluerridge"):
        assert selftest.run() is False
    assert order == ["sources", "routes", "genie"]
    assert _log_text(caplog).splitlines()[-1] == "selftest done ok=False"
