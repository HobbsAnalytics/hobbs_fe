"""Lakebase (Postgres) access as the app's service principal.

* The platform injects PGHOST / PGPORT / PGUSER (the SP client id) / PGDATABASE; there is no static password.
* Each *new* pooled connection mints a fresh OAuth database credential with
  ``WorkspaceClient().postgres.generate_database_credential(endpoint=LAKEBASE_ENDPOINT)`` (valid about an hour).
* Credential refresh = pool recycling: ``max_lifetime`` (30 min) is shorter than the token TTL, so every connection is
  replaced, with a freshly generated credential, before its token could expire. An already-open connection keeps
  working past token expiry (the token is only checked at login), so no mid-query failures.
* ``query`` takes SQL with ``%s`` placeholders and a params tuple, never formatted SQL.
"""
import logging
import os
import threading
from typing import Any, Optional, Sequence

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool, PoolTimeout

from backend import config
from backend.auth import sp_workspace_client
from backend.errors import DataUnavailable

logger = logging.getLogger("bluerridge.lakebase")

POOL_MAX_LIFETIME_S = 1800  # < ~3600 s credential TTL
_pool: Optional[ConnectionPool] = None
_lock = threading.Lock()


def _connect_with_fresh_credential() -> psycopg.Connection:
    cred = sp_workspace_client().postgres.generate_database_credential(endpoint=config.LAKEBASE_ENDPOINT)
    return psycopg.Connection.connect(
        host=os.environ["PGHOST"],
        port=int(os.environ.get("PGPORT", "5432")),
        dbname=config.LAKEBASE_DATABASE,
        user=os.environ["PGUSER"],
        password=cred.token,
        sslmode="require",
        connect_timeout=10,
        autocommit=True,
        row_factory=dict_row,
    )


class _FreshCredentialConnection(psycopg.Connection):
    """Lets ConnectionPool create connections through ``_connect_with_fresh_credential``."""

    @classmethod
    def connect(cls, conninfo: str = "", **kwargs):  # type: ignore[override]
        return _connect_with_fresh_credential()


def get_pool() -> ConnectionPool:
    global _pool
    with _lock:
        if _pool is None:
            pool = ConnectionPool(
                conninfo="",
                connection_class=_FreshCredentialConnection,
                min_size=1,
                max_size=4,
                max_lifetime=POOL_MAX_LIFETIME_S,
                timeout=15,
                open=False,
                name="lakebase",
            )
            pool.open()
            _pool = pool
        return _pool


def query(sql: str, params: Optional[Sequence[Any]] = None) -> list[dict]:
    """Run one parameterized read; rows come back as dicts. Any connectivity/permission problem is DataUnavailable."""
    try:
        with get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return list(cur.fetchall())
    except (psycopg.Error, PoolTimeout) as e:
        logger.warning("lakebase query failed: %s", type(e).__name__)
        raise DataUnavailable(f"Lakebase query failed ({type(e).__name__})") from None
