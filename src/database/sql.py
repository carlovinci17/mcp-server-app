import struct
import time
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from src.azure.identity import get_credential
from src.core.settings import get_settings

_SQL_COPT_SS_ACCESS_TOKEN = 1256
_SQL_SCOPE = "https://database.windows.net/.default"
_TOKEN_STRUCT_PREFIX_FMT = "<I"

# Azure SQL Serverless rejects the first connection attempt fast while
# resuming from auto-pause, rather than blocking a single attempt until the
# resume finishes. A longer Connection Timeout doesn't help; the caller has
# to retry the connection attempt itself after a short delay.
_CONNECT_RETRY_ATTEMPTS = 5
_CONNECT_RETRY_DELAY_SECONDS = 8


def _access_token_struct() -> bytes:
    token = get_credential().get_token(_SQL_SCOPE).token
    token_bytes = token.encode("utf-16-le")
    return struct.pack(
        f"{_TOKEN_STRUCT_PREFIX_FMT}{len(token_bytes)}s", len(token_bytes), token_bytes
    )


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    if not settings.sql_enabled:
        raise RuntimeError("AZURE_SQL_SERVER / AZURE_SQL_DATABASE are not configured")

    odbc_connection_string = (
        "Driver={ODBC Driver 18 for SQL Server};"
        f"Server=tcp:{settings.azure_sql_server},1433;"
        f"Database={settings.azure_sql_database};"
        "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
    )
    engine = create_engine(
        f"mssql+pyodbc:///?odbc_connect={odbc_connection_string}",
        pool_pre_ping=True,
        # AAD access tokens expire in ~60-90 minutes; recycle pooled connections
        # well before that so a stale token doesn't get reused on checkout.
        pool_recycle=1700,
    )

    @event.listens_for(engine, "do_connect")
    def _provide_access_token(dialect, conn_rec, cargs, cparams):
        cparams["attrs_before"] = {_SQL_COPT_SS_ACCESS_TOKEN: _access_token_struct()}

    return engine


@lru_cache
def get_session_factory() -> sessionmaker:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def _ensure_connected(session: Session) -> None:
    for attempt in range(_CONNECT_RETRY_ATTEMPTS):
        try:
            session.connection()
            return
        except OperationalError:
            if attempt == _CONNECT_RETRY_ATTEMPTS - 1:
                raise
            time.sleep(_CONNECT_RETRY_DELAY_SECONDS)


@contextmanager
def get_session() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        _ensure_connected(session)
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
