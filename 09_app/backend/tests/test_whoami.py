"""/api/whoami and backend.auth: forwarded-header identity, OBO vs SP, and token hygiene.

Header names come from 09_app/backend/AUTH_NOTES.md (Databricks Apps docs + databricks/app-templates).
"""
import logging

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from backend import auth
from backend.main import create_app

# A recognizable fake; it must never appear in any response body, response header or log line.
PLANTED_VALUE = "planted-obo-value-7c1e9a"

OBO_HEADERS = {
    "x-forwarded-email": "joseph.hobbs@databricks.com",
    "x-forwarded-user": "4242424242@1111",
    "x-forwarded-preferred-username": "joseph.hobbs@databricks.com",
    "x-forwarded-access-token": PLANTED_VALUE,
}


@pytest.fixture()
def client(tmp_path):
    (tmp_path / "index.html").write_text("<html><body>SPA-SHELL</body></html>")
    return TestClient(create_app(static_dir=tmp_path))


def _request(headers: dict) -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    return Request({"type": "http", "method": "GET", "path": "/", "headers": raw})


# --- /api/whoami ---------------------------------------------------------------------------------------------------

def test_whoami_obo_with_forwarded_headers(client):
    r = client.get("/api/whoami", headers=OBO_HEADERS)
    assert r.status_code == 200
    j = r.json()
    assert j["email"] == "joseph.hobbs@databricks.com"
    assert j["user_name"] == "joseph.hobbs@databricks.com"
    assert j["auth_mode"] == "OBO"


def test_whoami_user_name_falls_back_to_forwarded_user(client):
    headers = {k: v for k, v in OBO_HEADERS.items() if k != "x-forwarded-preferred-username"}
    j = client.get("/api/whoami", headers=headers).json()
    assert j["user_name"] == "4242424242@1111"
    assert j["auth_mode"] == "OBO"


def test_whoami_without_token_is_sp_and_keeps_header_identity(client):
    r = client.get("/api/whoami", headers={
        "x-forwarded-email": "joseph.hobbs@databricks.com",
        "x-forwarded-user": "joseph.hobbs",
    })
    assert r.status_code == 200
    j = r.json()
    assert j["auth_mode"] == "SP"
    assert j["email"] == "joseph.hobbs@databricks.com"
    assert j["user_name"] == "joseph.hobbs"


def test_whoami_no_headers_at_all_is_sp_with_nulls(client):
    j = client.get("/api/whoami").json()
    assert j == {"email": None, "user_name": None, "auth_mode": "SP"}


def test_whoami_blank_token_is_not_obo(client):
    j = client.get("/api/whoami", headers={"x-forwarded-access-token": "   "}).json()
    assert j["auth_mode"] == "SP"


def test_whoami_never_returns_or_logs_the_token(client, caplog):
    caplog.set_level(logging.DEBUG)
    r = client.get("/api/whoami", headers=OBO_HEADERS)
    assert r.status_code == 200
    assert PLANTED_VALUE not in r.text
    assert set(r.json()) == {"email", "user_name", "auth_mode"}
    for name, value in r.headers.items():
        assert PLANTED_VALUE not in value, name
    assert PLANTED_VALUE not in caplog.text
    # The request log does record who and how (email + auth_mode), just never the token.
    assert "joseph.hobbs@databricks.com" in caplog.text
    assert "OBO" in caplog.text


def test_whoami_is_not_swallowed_by_the_spa(client):
    r = client.get("/api/whoami", headers=OBO_HEADERS)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    assert "SPA-SHELL" not in r.text
    # Neighbouring unknown /api paths are still 404s, and client routes still get the SPA.
    assert client.get("/api/whoami/extra").status_code == 404
    assert "SPA-SHELL" in client.get("/compliance").text


# --- backend.auth --------------------------------------------------------------------------------------------------

def test_get_user_token_reads_forwarded_header():
    assert auth.get_user_token(_request(OBO_HEADERS)) == PLANTED_VALUE
    assert auth.get_user_token(_request({"X-Forwarded-Access-Token": PLANTED_VALUE})) == PLANTED_VALUE
    assert auth.get_user_token(_request({})) is None
    assert auth.get_user_token(_request({"x-forwarded-access-token": ""})) is None


def test_user_workspace_client_without_token_is_401():
    with pytest.raises(HTTPException) as exc:
        auth.user_workspace_client(_request({"x-forwarded-email": "joseph.hobbs@databricks.com"}))
    assert exc.value.status_code == 401
    assert "x-forwarded-access-token" in exc.value.detail.lower()


def test_user_workspace_client_uses_pat_auth_with_the_forwarded_token(monkeypatch):
    calls = []
    monkeypatch.setattr(auth, "WorkspaceClient", lambda **kw: calls.append(kw) or object())
    auth.user_workspace_client(_request(OBO_HEADERS))
    # auth_type="pat" is mandatory: the app env also holds the SP's client id/secret (see AUTH_NOTES.md).
    assert calls == [{"token": PLANTED_VALUE, "auth_type": "pat"}]


def test_user_workspace_client_is_built_per_request(monkeypatch):
    built = []
    monkeypatch.setattr(auth, "WorkspaceClient", lambda **kw: built.append(kw["token"]) or object())
    auth.user_workspace_client(_request({"x-forwarded-access-token": "planted-a"}))
    auth.user_workspace_client(_request({"x-forwarded-access-token": "planted-b"}))
    assert built == ["planted-a", "planted-b"]


def test_sp_workspace_client_is_default_auth_and_cached(monkeypatch):
    calls = []
    monkeypatch.setattr(auth, "WorkspaceClient", lambda **kw: calls.append(kw) or object())
    auth.sp_workspace_client.cache_clear()
    try:
        first = auth.sp_workspace_client()
        assert auth.sp_workspace_client() is first
        assert calls == [{}]  # no token, no auth_type: SDK default auth (app SP from env)
    finally:
        auth.sp_workspace_client.cache_clear()


def test_identity_does_not_build_a_client(monkeypatch):
    def boom(**kw):
        raise AssertionError("identity() must only read headers")
    monkeypatch.setattr(auth, "WorkspaceClient", boom)
    assert auth.identity(_request(OBO_HEADERS)) == {
        "email": "joseph.hobbs@databricks.com",
        "user_name": "joseph.hobbs@databricks.com",
        "auth_mode": "OBO",
    }
