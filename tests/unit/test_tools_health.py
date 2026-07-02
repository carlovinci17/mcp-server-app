import json

import azure.functions as func

from src.tools import health


def test_health_http_returns_server_health_json(monkeypatch):
    monkeypatch.setattr(health, "_server_health", lambda: json.dumps({"status": "ok"}))

    request = func.HttpRequest(method="GET", url="/api/health", body=b"")
    response = health._health_http(request)

    assert response.status_code == 200
    assert json.loads(response.get_body()) == {"status": "ok"}
