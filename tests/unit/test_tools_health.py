import json

import azure.functions as func

from src.tools import health


def test_health_http_returns_immediately_without_waiting_on_checks(monkeypatch):
    started_targets = []

    class FakeThread:
        def __init__(self, target, daemon=False):
            self.target = target
            self.daemon = daemon

        def start(self):
            started_targets.append(self.target)

    monkeypatch.setattr(health.threading, "Thread", FakeThread)

    request = func.HttpRequest(method="GET", url="/api/health", body=b"")
    response = health._health_http(request)

    assert response.status_code == 200
    assert json.loads(response.get_body()) == {"status": "warming"}
    assert started_targets == [health._check_sql, health._check_blob]


def test_tools_http_groups_tools_by_category_with_descriptions():
    request = func.HttpRequest(method="GET", url="/api/tools", body=b"")
    response = health._tools_http(request)

    assert response.status_code == 200
    payload = json.loads(response.get_body())
    groups_by_category = {g["category"]: g["tools"] for g in payload["groups"]}

    assert set(groups_by_category.keys()) == set(health._CAPABILITIES.keys())
    customer_tools = {t["name"]: t["description"] for t in groups_by_category["customers"]}
    assert customer_tools["search_customers"] == "Search customers by name, industry, or region."


def test_tools_http_covers_every_tool_in_capabilities():
    request = func.HttpRequest(method="GET", url="/api/tools", body=b"")
    response = health._tools_http(request)

    payload = json.loads(response.get_body())
    all_tool_names = {t["name"] for g in payload["groups"] for t in g["tools"]}
    expected_names = {name for names in health._CAPABILITIES.values() for name in names}

    assert all_tool_names == expected_names
    # every tool must have a real, non-empty description - not a silent gap
    for group in payload["groups"]:
        for tool in group["tools"]:
            assert tool["description"], f"{tool['name']} has no description"
