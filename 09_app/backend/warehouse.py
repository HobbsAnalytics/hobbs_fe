"""SQL warehouse access as the app's service principal (Statement Execution API, named parameters only).

Unity Catalog row filters see the SP's ``current_user()``, which is why the SP has a ``discipline_access`` row.
User input only ever travels in ``parameters``; the statement text is a constant owned by the route.
"""
import logging
from typing import Optional

from databricks.sdk.service.sql import ExecuteStatementRequestOnWaitTimeout, StatementParameterListItem

from backend import config
from backend.auth import sp_workspace_client
from backend.errors import DataUnavailable

logger = logging.getLogger("bluerridge.warehouse")

WAIT_TIMEOUT = "30s"
_INT = {"BYTE", "SHORT", "INT", "LONG"}
_FLOAT = {"FLOAT", "DOUBLE", "DECIMAL"}


def _convert(value, type_name: str):
    if value is None:
        return None
    if type_name in _INT:
        return int(value)
    if type_name in _FLOAT:
        return float(value)
    if type_name == "BOOLEAN":
        return str(value).lower() == "true"
    return value


def query(sql: str, params: Optional[dict] = None) -> list[dict]:
    """Execute ``sql`` (with ``:name`` markers) on the warehouse; return rows as dicts."""
    parameters = [StatementParameterListItem(name=k, value=None if v is None else str(v))
                  for k, v in (params or {}).items()] or None
    try:
        resp = sp_workspace_client().statement_execution.execute_statement(
            statement=sql,
            warehouse_id=config.WAREHOUSE_ID,
            parameters=parameters,
            wait_timeout=WAIT_TIMEOUT,
            on_wait_timeout=ExecuteStatementRequestOnWaitTimeout.CANCEL,
        )
    except Exception as e:  # SDK / network errors: never leak their text
        logger.warning("warehouse call failed: %s", type(e).__name__)
        raise DataUnavailable(f"SQL warehouse is unreachable ({type(e).__name__})") from None
    state = resp.status.state.value if resp.status and resp.status.state else "UNKNOWN"
    if state != "SUCCEEDED":
        logger.warning("warehouse statement state=%s", state)
        raise DataUnavailable(f"SQL warehouse statement did not complete (state {state})")
    cols = [(c.name, c.type_name.value if c.type_name else "STRING") for c in resp.manifest.schema.columns]
    data = resp.result.data_array if resp.result and resp.result.data_array else []
    return [{name: _convert(v, t) for (name, t), v in zip(cols, row)} for row in data]
