"""Genie for the chat, for whichever ``WorkspaceClient`` the caller passes (the user's OBO client in /api/chat, the app
service principal in the startup self-test). Both go through the same code path.

Transport (research and evidence: backend/AUTH_NOTES.md, "Genie transport for the chat"):

* ``mcp`` (default): the **managed Genie MCP server for this space**, ``POST {host}/api/2.0/mcp/genie/{space_id}``
  (Public Preview, OAuth scope ``genie``). The app speaks MCP's JSON-RPC ``tools/call`` itself: tool
  ``query_space_<space_id>`` (args ``query``, optional ``conversation_id``), then ``poll_response_<space_id>`` (args
  ``conversation_id``, ``message_id``) until the status is terminal. Each result's ``structuredContent`` carries
  ``textAttachments`` (Genie's answer), ``queryAttachments[].query`` (the SQL), ``queryAttachments[].statement_response``
  (columns and rows) and ``conversationId``. The ``databricks-mcp`` client library is not used: it pulls in about 108
  packages (full mlflow among them) for what is one HTTP POST.
* ``conversation_api``: the Genie Conversation API on the same space (``w.genie.start_conversation`` /
  ``create_message`` -> ``get_message`` -> ``get_message_attachment_query_result``). Used only when
  ``GENIE_TRANSPORT=conversation_api``, or as a fallback when the MCP endpoint refuses the *first* call (403, 404,
  5xx or a JSON-RPC protocol error). A message has not been created at that point, so the fallback cannot ask twice.

The MCP POST bypasses the SDK's retrying HTTP client on purpose: the SDK retries read timeouts for up to 300 s, and a
retried ``query_space`` would post the question to Genie a second time. Instead each call gets the remaining
deadline as its read timeout and is never retried. The Authorization header comes from ``w.config.authenticate()``
(the SDK's own header provider), lives only in the request, and is never logged, stored or put into an error message.
"""
import itertools
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

import requests
from databricks.sdk.errors import DatabricksError, NotFound, PermissionDenied, Unauthenticated

from backend import config

logger = logging.getLogger("bluerridge.genie")

DEFAULT_DEADLINE_S = 105.0   # Genie polling budget; the route's wall clock (110 s) is the backstop
POLL_INTERVAL_S = 1.0
CONNECT_TIMEOUT_S = 10.0
TERMINAL_BAD = {"FAILED", "CANCELLED", "QUERY_RESULT_EXPIRED"}
TRANSPORT_MCP, TRANSPORT_CONV = "mcp", "conversation_api"
_INT = {"BYTE", "SHORT", "INT", "LONG"}
_FLOAT = {"FLOAT", "DOUBLE", "DECIMAL"}
_ids = itertools.count(1)

# Shown to the PM verbatim, so no SQL, hosts, ids or exception text.
SAFE_MESSAGES = {
    "unauthenticated": "Your Databricks session has expired. Reload the page and ask again.",
    "forbidden": "You don't have access to the Genie space behind this chat.",
    "not_found": "The Genie space behind this chat is not available.",
    "unavailable": "Genie is unavailable right now. Try again in a moment.",
    "protocol": "Genie is unavailable right now. Try again in a moment.",
    "failed": "Genie could not answer that question. Try rephrasing it.",
    "no_data_access": "Genie could not read the data for that answer with your permissions.",
    "timeout": "Genie did not answer within 110 seconds. Try a narrower question.",
}
# MCP refusals on the first call that justify trying the Conversation API instead (never 401 or a timeout).
_FALLBACK_KINDS = {"forbidden", "not_found", "unavailable", "protocol"}


class GenieError(Exception):
    """A Genie call failed. ``kind`` is a short code; ``str(e)`` is the safe, user-facing message."""

    def __init__(self, kind: str = "unavailable"):
        self.kind = kind if kind in SAFE_MESSAGES else "unavailable"
        super().__init__(SAFE_MESSAGES[self.kind])


class GenieTimeout(GenieError):
    def __init__(self):
        super().__init__("timeout")


class _McpRefused(GenieError):
    """The MCP endpoint refused the first call (no Genie message exists yet)."""


@dataclass
class GenieTurn:
    transport: str
    conversation_id: Optional[str]
    message_id: Optional[str]
    status: str
    text: str = ""                  # Genie's text attachments, joined
    description: str = ""           # the query attachment's description
    sql: Optional[str] = None
    columns: list = field(default_factory=list)
    rows: list = field(default_factory=list)     # typed cells (int / float / bool / str / None)
    row_count: int = 0              # total rows Genie reported (may exceed len(rows))
    truncated: bool = False         # Genie / the statement reported a truncated result
    suggested: list = field(default_factory=list)

    def headline(self):
        """The first numeric cell of the first row (for the self-test), else None."""
        for cell in (self.rows[0] if self.rows else []):
            if isinstance(cell, (int, float)) and not isinstance(cell, bool):
                return cell
        return None


# --- shared result parsing ---------------------------------------------------------------------------------------

def _convert(value, type_name: str):
    if value is None:
        return None
    try:
        if type_name in _INT:
            return int(value)
        if type_name in _FLOAT:
            return float(value)
    except (TypeError, ValueError):
        return value
    if type_name == "BOOLEAN":
        return value if isinstance(value, bool) else str(value).lower() == "true"
    return value


def _cell(v):
    """One protobuf-style cell from the MCP server ({"string_value": ...} etc.)."""
    if not isinstance(v, dict):
        return v
    for key in ("string_value", "number_value", "bool_value"):
        if key in v:
            return v[key]
    return None  # null_value, or an unknown/empty cell


def _cells(row) -> list:
    """A row as a list: MCP rows are {"values": [cells]}, Conversation API rows are plain lists of strings."""
    if isinstance(row, dict):
        return [_cell(v) for v in row.get("values") or []]
    return list(row or [])


def _table(sr: Optional[dict]):
    """(columns, rows, row_count, truncated) from a Statement Execution response dict."""
    if not sr:
        return [], [], 0, False
    manifest = sr.get("manifest") or {}
    cols = (manifest.get("schema") or {}).get("columns") or []
    names = [c.get("name") for c in cols]
    types_ = [c.get("type_name") or "STRING" for c in cols]
    data = (sr.get("result") or {}).get("data_array") or []
    rows = [[_convert(v, t) for v, t in zip(_cells(r), types_)] for r in data]
    total = manifest.get("total_row_count")
    total = int(total) if total is not None else len(rows)
    return names, rows, max(total, len(rows)), bool(manifest.get("truncated"))


def _notify(cb: Optional[Callable[[str], None]], conversation_id: Optional[str]) -> None:
    if cb and conversation_id:
        try:
            cb(conversation_id)
        except Exception as e:  # a UI callback must never break the Genie call
            logger.warning("genie on_conversation callback failed: %s", type(e).__name__)


def _remaining(deadline: float) -> float:
    left = deadline - time.monotonic()
    if left <= 0:
        raise GenieTimeout()
    return left


def _error_kind_from_text(err: str) -> str:
    return "no_data_access" if any(s in (err or "") for s in ("INSUFFICIENT_PERMISSIONS", "PERMISSION_DENIED")) \
        else "failed"


# --- transport: managed Genie MCP server -------------------------------------------------------------------------

def _post(url: str, headers: dict, payload: dict, timeout):
    """One JSON-RPC POST, no retries. Returns (status_code, parsed JSON or None). Patched in tests."""
    r = requests.post(url, json=payload, headers=headers, timeout=timeout)
    try:
        body = r.json()
    except ValueError:
        body = None
    return r.status_code, body


def _mcp_tool(w, space_id: str, tool: str, arguments: dict, deadline: float, first: bool) -> dict:
    url = f"{w.config.host.rstrip('/')}/api/2.0/mcp/genie/{space_id}"
    headers = {"Content-Type": "application/json", "Accept": "application/json", **w.config.authenticate()}
    payload = {"jsonrpc": "2.0", "id": next(_ids), "method": "tools/call",
               "params": {"name": f"{tool}_{space_id}", "arguments": arguments}}
    refused = _McpRefused if first else GenieError
    try:
        status, body = _post(url, headers, payload, (CONNECT_TIMEOUT_S, max(1.0, _remaining(deadline))))
    except requests.Timeout:
        raise GenieTimeout() from None
    except requests.RequestException as e:
        logger.warning("genie mcp %s transport error: %s", tool, type(e).__name__)
        raise refused("unavailable") from None
    if status == 401:
        raise GenieError("unauthenticated")
    if status == 403:
        raise refused("forbidden")
    if status == 404:
        raise refused("not_found")
    if status >= 400 or not isinstance(body, dict):
        logger.warning("genie mcp %s http_status=%s", tool, status)
        raise refused("unavailable")
    if body.get("error"):
        logger.warning("genie mcp %s jsonrpc_error code=%s", tool, (body["error"] or {}).get("code"))
        raise refused("protocol")
    result = body.get("result") or {}
    if result.get("isError"):
        logger.warning("genie mcp %s tool returned isError", tool)
        raise GenieError("failed")
    sc = result.get("structuredContent")
    if sc is None:
        try:
            sc = json.loads(((result.get("content") or [{}])[0]).get("text") or "{}")
        except (ValueError, AttributeError, IndexError):
            raise GenieError("protocol") from None
    return sc if isinstance(sc, dict) else {}


def _mcp_turn(sc: dict) -> GenieTurn:
    c = sc.get("content") or {}
    texts = [t.strip() for t in c.get("textAttachments") or [] if isinstance(t, str) and t.strip()]
    qa = next((q for q in c.get("queryAttachments") or [] if isinstance(q, dict) and q.get("query")), None)
    cols, rows, total, truncated = _table((qa or {}).get("statement_response"))
    return GenieTurn(transport=TRANSPORT_MCP, conversation_id=sc.get("conversationId"),
                     message_id=sc.get("messageId"), status=str(sc.get("status") or "").upper(),
                     text="\n\n".join(texts), description=(qa or {}).get("description") or "",
                     sql=(qa or {}).get("query"), columns=cols, rows=rows, row_count=total, truncated=truncated,
                     suggested=[s for s in c.get("suggestedQuestions") or [] if isinstance(s, str)])


def _mcp_ask(w, space_id, message, conversation_id, deadline, on_conversation) -> GenieTurn:
    args = {"query": message}
    if conversation_id:
        args["conversation_id"] = conversation_id
    t = _mcp_turn(_mcp_tool(w, space_id, "query_space", args, deadline, first=True))
    _notify(on_conversation, t.conversation_id)
    while t.status != "COMPLETED":
        if t.status in TERMINAL_BAD:
            raise GenieError("failed")
        if not (t.conversation_id and t.message_id):
            raise GenieError("protocol")
        time.sleep(min(POLL_INTERVAL_S, _remaining(deadline)))
        t = _mcp_turn(_mcp_tool(w, space_id, "poll_response",
                                {"conversation_id": t.conversation_id, "message_id": t.message_id},
                                deadline, first=False))
    return t


# --- transport: Genie Conversation API (SDK) ---------------------------------------------------------------------

def _conv_ask(w, space_id, message, conversation_id, deadline, on_conversation) -> GenieTurn:
    try:
        if conversation_id:
            waiter = w.genie.create_message(space_id, conversation_id, message)
        else:
            waiter = w.genie.start_conversation(space_id, message)
        cid, mid = waiter.conversation_id, waiter.message_id
        _notify(on_conversation, cid)
        while True:
            m = w.genie.get_message(space_id, cid, mid).as_dict()
            status = str(m.get("status") or "").upper()
            if status == "COMPLETED":
                break
            if status in TERMINAL_BAD:
                raise GenieError(_error_kind_from_text(json.dumps(m.get("error") or {})))
            time.sleep(min(POLL_INTERVAL_S, _remaining(deadline)))
        texts, suggested, qa = [], [], None
        for a in m.get("attachments") or []:
            if (a.get("text") or {}).get("content"):
                texts.append(a["text"]["content"].strip())
            if (a.get("query") or {}).get("query") and qa is None:
                qa = a
            suggested += (a.get("suggested_questions") or {}).get("questions") or []
        cols, rows, total, truncated = [], [], 0, False
        if qa and qa.get("attachment_id"):
            _remaining(deadline)
            qr = w.genie.get_message_attachment_query_result(space_id, cid, mid, qa["attachment_id"])
            sr = qr.statement_response.as_dict() if qr.statement_response else None
            cols, rows, total, truncated = _table(sr)
        q = (qa or {}).get("query") or {}
        return GenieTurn(transport=TRANSPORT_CONV, conversation_id=cid, message_id=mid, status="COMPLETED",
                         text="\n\n".join(t for t in texts if t), description=q.get("description") or "",
                         sql=q.get("query"), columns=cols, rows=rows, row_count=total, truncated=truncated,
                         suggested=suggested)
    except GenieError:
        raise
    except Unauthenticated:
        raise GenieError("unauthenticated") from None
    except PermissionDenied:
        raise GenieError("forbidden") from None
    except NotFound:
        raise GenieError("not_found") from None
    except DatabricksError as e:
        logger.warning("genie conversation_api error: %s", type(e).__name__)
        raise GenieError("unavailable") from None


# --- entry point -------------------------------------------------------------------------------------------------

def ask(w, message: str, conversation_id: Optional[str] = None, *, space_id: Optional[str] = None,
        deadline_s: float = DEFAULT_DEADLINE_S, transport: Optional[str] = None,
        on_conversation: Optional[Callable[[str], None]] = None) -> GenieTurn:
    """Ask the Genie space one question (or a follow-up) as whoever ``w`` authenticates as. Blocking.

    Calls ``on_conversation(conversation_id)`` as soon as the id is known. Raises ``GenieTimeout`` past the
    deadline and ``GenieError`` (safe message) for every other failure.
    """
    space_id = space_id or config.GENIE_SPACE_ID
    deadline = time.monotonic() + deadline_s
    chosen = (transport or os.getenv("GENIE_TRANSPORT") or TRANSPORT_MCP).strip().lower()
    if chosen == TRANSPORT_CONV:
        return _conv_ask(w, space_id, message, conversation_id, deadline, on_conversation)
    try:
        return _mcp_ask(w, space_id, message, conversation_id, deadline, on_conversation)
    except _McpRefused as e:
        if e.kind not in _FALLBACK_KINDS:
            raise
        logger.warning("genie mcp refused the first call (%s); falling back to conversation_api", e.kind)
        return _conv_ask(w, space_id, message, conversation_id, deadline, on_conversation)
