import pytest
from sqlalchemy.exc import DBAPIError, OperationalError

from src.database import sql
from src.database.sql import DatabaseUnavailableError, _ensure_connected


class _FakeSession:
    def __init__(self, side_effects):
        self._side_effects = iter(side_effects)
        self.attempts = 0

    def connection(self):
        self.attempts += 1
        effect = next(self._side_effects)
        if effect is not None:
            raise effect
        return "connected"


def _paused_error() -> DBAPIError:
    orig = Exception(
        "[HY000] [Microsoft][ODBC Driver 18 for SQL Server][SQL Server]This database has "
        "reached the monthly free amount allowance for the month of July 2026 and is paused "
        "(42119) (SQLDriverConnect)"
    )
    return DBAPIError("SELECT 1", {}, orig)


def test_ensure_connected_raises_friendly_error_when_free_tier_paused(monkeypatch):
    monkeypatch.setattr(sql.time, "sleep", lambda _: pytest.fail("should not retry"))
    session = _FakeSession([_paused_error()])

    with pytest.raises(DatabaseUnavailableError, match="free-tier"):
        _ensure_connected(session)

    assert session.attempts == 1


def test_ensure_connected_retries_transient_operational_error(monkeypatch):
    monkeypatch.setattr(sql.time, "sleep", lambda _: None)
    transient = OperationalError("SELECT 1", {}, Exception("resuming from auto-pause"))
    session = _FakeSession([transient, None])

    _ensure_connected(session)

    assert session.attempts == 2


def test_ensure_connected_reraises_non_operational_dbapi_error_immediately(monkeypatch):
    monkeypatch.setattr(sql.time, "sleep", lambda _: pytest.fail("should not retry"))
    other = DBAPIError("SELECT 1", {}, Exception("permission denied"))
    session = _FakeSession([other])

    with pytest.raises(DBAPIError):
        _ensure_connected(session)

    assert session.attempts == 1
