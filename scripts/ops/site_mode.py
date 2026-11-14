"""Switch web/staticwebapp.config.json between the live console and the
offline "contact me for a demo" page.

    uv run python scripts/ops/site_mode.py offline
    uv run python scripts/ops/site_mode.py online
    uv run python scripts/ops/site_mode.py status

Offline mode prepends routes that rewrite the console, any unknown path, and
/api/* to /offline.html, since the Function App backend is unlinked while
hibernated. (Azure rejects a route that sets both `rewrite` and
`statusCode`, so /api/* answers 200 with the offline page, not a 503.)
Everything else in the config - including /vera-how-it-works, which stays
live - is left untouched, and
`online` restores the original file byte for byte.

Only edits the file; the change reaches production when it's pushed to main
(the Static Web Apps workflow deploys web/). See docs/operations.md.
"""

import argparse
import json
import sys
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parents[2] / "web" / "staticwebapp.config.json"

OFFLINE_PAGE = "/offline.html"
CONSOLE_PAGE = "/index.html"

OFFLINE_ROUTES = [
    {"route": "/", "rewrite": OFFLINE_PAGE},
    {"route": "/index.html", "rewrite": OFFLINE_PAGE},
    {"route": "/api/*", "rewrite": OFFLINE_PAGE},
]


def is_offline(config: dict) -> bool:
    return config["navigationFallback"]["rewrite"] == OFFLINE_PAGE


def to_offline(config: dict) -> dict:
    # Always rebuild from the online form, so an offline config written by an
    # older version of this script is normalised rather than left as-is.
    config = to_online(config)
    config["routes"] = OFFLINE_ROUTES + config.get("routes", [])
    config["navigationFallback"]["rewrite"] = OFFLINE_PAGE
    return config


def to_online(config: dict) -> dict:
    config = json.loads(json.dumps(config))
    # Any route pointing at the offline page belongs to offline mode,
    # including ones from older versions of OFFLINE_ROUTES.
    config["routes"] = [r for r in config.get("routes", []) if r.get("rewrite") != OFFLINE_PAGE]
    config["navigationFallback"]["rewrite"] = CONSOLE_PAGE
    return config


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("mode", choices=["offline", "online", "status"])
    mode = parser.parse_args().mode

    config = json.loads(CONFIG_PATH.read_text())
    if mode == "status":
        print("offline" if is_offline(config) else "online")
        return 0

    updated = to_offline(config) if mode == "offline" else to_online(config)
    if updated == config:
        print(f"Site config already {mode}.")
        return 0
    CONFIG_PATH.write_text(json.dumps(updated, indent=2) + "\n")
    print(f"Site config switched to {mode}: {CONFIG_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
