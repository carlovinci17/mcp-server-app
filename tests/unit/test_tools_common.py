import json

from src.database.sql import DatabaseUnavailableError
from src.tools._common import report_database_unavailable


def test_report_database_unavailable_converts_to_json_error():
    @report_database_unavailable
    def _tool() -> str:
        raise DatabaseUnavailableError("paused for the rest of the month")

    result = _tool()

    payload = json.loads(result)
    assert payload == {"error": "paused for the rest of the month"}


def test_report_database_unavailable_passes_through_on_success():
    @report_database_unavailable
    def _tool(value: str) -> str:
        return json.dumps({"value": value})

    result = _tool("ok")

    assert json.loads(result) == {"value": "ok"}
