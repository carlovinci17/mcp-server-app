import json

from tests.unit._script_loader import load_script

site_mode = load_script("scripts/ops/site_mode.py")


def _live_config() -> dict:
    return json.loads(site_mode.CONFIG_PATH.read_text())


def test_committed_config_is_online():
    assert not site_mode.is_offline(_live_config())


def test_offline_rewrites_console_api_and_fallback_to_offline_page():
    offline = site_mode.to_offline(_live_config())

    assert site_mode.is_offline(offline)
    routes = {r["route"]: r for r in offline["routes"]}
    assert routes["/"]["rewrite"] == "/offline.html"
    assert routes["/index.html"]["rewrite"] == "/offline.html"
    assert routes["/api/*"]["statusCode"] == 503
    assert offline["navigationFallback"]["rewrite"] == "/offline.html"


def test_offline_keeps_explainer_page_and_headers():
    config = _live_config()
    offline = site_mode.to_offline(config)

    assert {"route": "/vera-how-it-works", "rewrite": "/vera-how-it-works.html"} in offline[
        "routes"
    ]
    assert offline["globalHeaders"] == config["globalHeaders"]


def test_offline_then_online_round_trips_byte_for_byte():
    original_text = site_mode.CONFIG_PATH.read_text()
    config = json.loads(original_text)

    restored = site_mode.to_online(site_mode.to_offline(config))

    assert json.dumps(restored, indent=2) + "\n" == original_text


def test_switching_is_idempotent():
    config = _live_config()
    offline = site_mode.to_offline(config)

    assert site_mode.to_offline(offline) == offline
    assert site_mode.to_online(config) == config
