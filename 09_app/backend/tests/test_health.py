"""Scaffold tests: /health, SPA fallback and /api priority."""
import pytest
from fastapi.testclient import TestClient

from backend.main import create_app


@pytest.fixture()
def client(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log('x')")
    (tmp_path / "index.html").write_text("<html><body>SPA-SHELL</body></html>")
    return TestClient(create_app(static_dir=tmp_path))


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_client_route_returns_index_html(client):
    for path in ("/compliance", "/drawings/DWG-001", "/"):
        r = client.get(path)
        assert r.status_code == 200
        assert "SPA-SHELL" in r.text


def test_static_asset_served(client):
    r = client.get("/assets/app.js")
    assert r.status_code == 200
    assert "console.log" in r.text


def test_unknown_api_route_is_404_not_spa(client):
    r = client.get("/api/unknown")
    assert r.status_code == 404
    assert "SPA-SHELL" not in r.text


def test_missing_build_does_not_break_health(tmp_path):
    c = TestClient(create_app(static_dir=tmp_path / "nope"))
    assert c.get("/health").status_code == 200
