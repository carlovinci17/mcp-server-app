import json

from tests.unit._script_loader import load_script

site_mode = load_script("scripts/ops/site_mode.py")


def _online_config() -> dict:
    # The committed file may be in either mode (hibernate commits it offline),
    # so always start from its online form.
    return site_mode.to_online(json.loads(site_mode.CONFIG_PATH.read_text()))


def _azure_route_errors(config: dict) -> list[str]:
    # Azure Static Web Apps rejects these at deploy time; the local SWA CLI
    # emulator doesn't check them, so they're asserted here instead.
    errors = []
    for route in config["routes"]:
        if "statusCode" in route and ({"rewrite", "redirect"} & route.keys()):
            errors.append(f"{route['route']}: statusCode with rewrite/redirect")
    return errors


def test_online_config_serves_console():
    config = _online_config()

    assert not site_mode.is_offline(config)
    assert config["navigationFallback"]["rewrite"] == "/index.html"
    assert all(r.get("rewrite") != "/offline.html" for r in config["routes"])


def test_offline_rewrites_console_api_and_fallback_to_offline_page():
    offline = site_mode.to_offline(_online_config())

    assert site_mode.is_offline(offline)
    routes = {r["route"]: r for r in offline["routes"]}
    assert routes["/"]["rewrite"] == "/offline.html"
    assert routes["/index.html"]["rewrite"] == "/offline.html"
    assert routes["/api/*"]["rewrite"] == "/offline.html"
    assert offline["navigationFallback"]["rewrite"] == "/offline.html"


def test_both_modes_pass_azure_route_validation():
    online = _online_config()

    assert _azure_route_errors(online) == []
    assert _azure_route_errors(site_mode.to_offline(online)) == []


def test_offline_keeps_explainer_page_and_headers():
    config = _online_config()
    offline = site_mode.to_offline(config)

    assert {"route": "/vera-how-it-works", "rewrite": "/vera-how-it-works.html"} in offline[
        "routes"
    ]
    assert offline["globalHeaders"] == config["globalHeaders"]


def test_offline_then_online_round_trips_byte_for_byte():
    original_text = json.dumps(_online_config(), indent=2) + "\n"

    restored = site_mode.to_online(site_mode.to_offline(json.loads(original_text)))

    assert json.dumps(restored, indent=2) + "\n" == original_text


def test_switching_is_idempotent():
    config = _online_config()
    offline = site_mode.to_offline(config)

    assert site_mode.to_offline(offline) == offline
    assert site_mode.to_online(config) == config


def test_legacy_offline_config_is_repaired():
    # An earlier OFFLINE_ROUTES gave /api/* a statusCode alongside rewrite,
    # which Azure refused to deploy.
    legacy = site_mode.to_offline(_online_config())
    legacy["routes"][2] = {"route": "/api/*", "rewrite": "/offline.html", "statusCode": 503}
    assert _azure_route_errors(legacy)

    repaired = site_mode.to_offline(legacy)

    assert _azure_route_errors(repaired) == []
    assert repaired == site_mode.to_offline(_online_config())
    assert site_mode.to_online(legacy) == _online_config()
