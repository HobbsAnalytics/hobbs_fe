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
  ``create_message`` -> ``get_message`` -> ``get_message_attachment_query_result``). Used when
  ``GENIE_TRANSPORT=conversation_api``, or as a fallback, with the same client, when the MCP endpoint refuses the
  *first* call in a way that happens before Genie can have received the question:
  - HTTP 400, 403, 404, 405, 406 or 415;
  - JSON-RPC -32700, -32600, -32601 or -32602 (parse error, invalid request, unknown method, invalid params);
  - the connection could not be opened (connect timeout, connection refused, DNS).
  Nothing else falls back: 5xx, 429, a non-JSON body, other JSON-RPC codes, a connection dropped after the request
  went out, a read timeout, or any error on a poll call. In those cases Genie may already hold the message, and
  asking again could ask it twice. They become safe errors instead.
  When ``query_space`` completes with SQL but no ``statement_response``, the rows are fetched for that same message
  through the Conversation API (``get_message`` -> ``get_message_attachment_query_result``). Genie is not asked again.

The MCP POST bypasses the SDK's retrying HTTP client on purpose: the SDK retries read timeouts for up to 300 s, and a
retried ``query_space`` would post the question to Genie a second time. Instead each call gets the remaining
deadline as its read timeout and is never retried. The Authorization header comes from ``w.config.authenticate()``
(the SDK's own header provider), lives only in the request, and is never logged, stored or put into an error message.
The client sends stateless ``tools/call`` requests: there is no ``initialize`` handshake, and the
``Accept: application/json`` header does not include ``text/event-stream``. That is what the live server accepts (see
AUTH_NOTES). A stricter server would answer with one of the pre-execution refusals above, which triggers the
fallback.
"""
import itertools
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

import requests
import urllib3
from databricks.sdk.errors import (
    DatabricksError,
    NotFound,
    PermissionDenied,
    Unauthenticated,
)

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
# First-call MCP refusals that happen before Genie can have the question; only these may fall back.
_PRE_EXECUTION_HTTP = {400: "protocol", 403: "forbidden", 404: "not_found", 405: "protocol", 406: "protocol",
                       415: "protocol"}
_PRE_EXECUTION_JSONRPC = {-32700, -32600, -32601, -32602}


class GenieError(Exception):
    """A Genie call failed. ``kind`` is a short code; ``str(e)`` is the safe, user-facing message.

    ``transport`` is set by ``ask()`` to the transport that raised it ("mcp" or "conversation_api"); None when the
    failure was not inside a transport (e.g. the route's own wall clock).
    """

    def __init__(self, kind: str = "unavailable"):
        self.kind = kind if kind in SAFE_MESSAGES else "unavailable"
        self.transport: Optional[str] = None
        super().__init__(SAFE_MESSAGES[self.kind])


class GenieTimeout(GenieError):
    def __init__(self):
        super().__init__("timeout")


class _McpRefused(GenieError):
    """The MCP endpoint refused the first call before Genie could have the question (safe to fall back)."""


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


def _never_sent(e: requests.RequestException) -> bool:
    """True only when the connection itself could not be opened, so the request cannot have reached Genie."""
    if isinstance(e, requests.ConnectTimeout):
        return True
    if isinstance(e, requests.ConnectionError):
        inner = e.args[0] if e.args else None
        reason = getattr(inner, "reason", inner)
        return isinstance(reason, urllib3.exceptions.NewConnectionError)  # refused, unreachable, DNS failure
    return False


def _mcp_tool(w, space_id: str, tool: str, arguments: dict, deadline: float, first: bool) -> dict:
    url = f"{w.config.host.rstrip('/')}/api/2.0/mcp/genie/{space_id}"
    headers = {"Content-Type": "application/json", "Accept": "application/json", **w.config.authenticate()}
    request_id = next(_ids)
    payload = {"jsonrpc": "2.0", "id": request_id, "method": "tools/call",
               "params": {"name": f"{tool}_{space_id}", "arguments": arguments}}
    # Only a first-call refusal that precedes execution may fall back; everything else is a plain GenieError.
    refused = _McpRefused if first else GenieError
    try:
        status, body = _post(url, headers, payload, (CONNECT_TIMEOUT_S, max(1.0, _remaining(deadline))))
    except requests.RequestException as e:
        if _never_sent(e):
            logger.warning("genie mcp %s could not connect: %s", tool, type(e).__name__)
            raise refused("unavailable") from None
        if isinstance(e, requests.Timeout):
            raise GenieTimeout() from None
        logger.warning("genie mcp %s transport error after send: %s", tool, type(e).__name__)
        raise GenieError("unavailable") from None
    if status == 401:
        raise GenieError("unauthenticated")
    if status in _PRE_EXECUTION_HTTP:
        logger.warning("genie mcp %s refused http_status=%s", tool, status)
        raise refused(_PRE_EXECUTION_HTTP[status])
    if status >= 400 or not isinstance(body, dict):
        logger.warning("genie mcp %s http_status=%s body_type=%s", tool, status, type(body).__name__)
        raise GenieError("unavailable")
    rid = body.get("id")
    if rid is not None and str(rid) != str(request_id):
        logger.warning("genie mcp %s response id does not match the request", tool)
        raise GenieError("protocol")
    if body.get("error") is not None:
        err = body["error"]
        code = err.get("code") if isinstance(err, dict) else None
        code = code if isinstance(code, int) and not isinstance(code, bool) else None
        logger.warning("genie mcp %s jsonrpc_error code=%s error_type=%s", tool, code, type(err).__name__)
        raise (refused if code in _PRE_EXECUTION_JSONRPC else GenieError)("protocol")
    result = body.get("result") if isinstance(body.get("result"), dict) else {}
    if result.get("isError"):
        logger.warning("genie mcp %s tool returned isError", tool)
        raise GenieError("failed")
    sc = result.get("structuredContent")
    if sc is None:
        try:
            sc = json.loads(((result.get("content") or [{}])[0]).get("text") or "{}")
        except (ValueError, AttributeError, IndexError, TypeError):
            raise GenieError("protocol") from None
    return sc if isinstance(sc, dict) else {}


def _content(sc: dict) -> dict:
    c = sc.get("content")
    return c if isinstance(c, dict) else {}


def _query_attachment(c: dict) -> Optional[dict]:
    return next((q for q in c.get("queryAttachments") or [] if isinstance(q, dict) and q.get("query")), None)


def _mcp_turn(sc: dict) -> GenieTurn:
    c = _content(sc)
    texts = [t.strip() for t in c.get("textAttachments") or [] if isinstance(t, str) and t.strip()]
    qa = _query_attachment(c)
    cols, rows, total, truncated = _table((qa or {}).get("statement_response"))
    return GenieTurn(transport=TRANSPORT_MCP, conversation_id=sc.get("conversationId"),
                     message_id=sc.get("messageId"), status=str(sc.get("status") or "").upper(),
                     text="\n\n".join(texts), description=(qa or {}).get("description") or "",
                     sql=(qa or {}).get("query"), columns=cols, rows=rows, row_count=total, truncated=truncated,
                     suggested=[s for s in c.get("suggestedQuestions") or [] if isinstance(s, str)])


def _keys(d) -> list:
    """Key names only, for parse warnings (never values)."""
    return sorted(str(k) for k in d) if isinstance(d, dict) else []


def _attachment_table(w, space_id, cid, mid, attachment_id):
    qr = w.genie.get_message_attachment_query_result(space_id, cid, mid, attachment_id)
    sr = qr.statement_response.as_dict() if qr.statement_response else None
    return _table(sr), sr is not None


def _fetch_mcp_rows(w, space_id: str, t: GenieTurn) -> GenieTurn:
    """MCP completed with SQL but no statement_response: read that same message's result through the Conversation
    API (no new question). On any failure keep the turn as it is (answer and SQL still shown, no table)."""
    try:
        m = w.genie.get_message(space_id, t.conversation_id, t.message_id).as_dict()
        att = next((a for a in m.get("attachments") or []
                    if (a.get("query") or {}).get("query") and a.get("attachment_id")), None)
        if att is None:
            logger.warning("genie mcp result fetch: message has no query attachment (attachment keys=%s)",
                           [_keys(a) for a in m.get("attachments") or []])
            return t
        (cols, rows, total, truncated), _ = _attachment_table(w, space_id, t.conversation_id, t.message_id,
                                                              att["attachment_id"])
    except Exception as e:  # never fail an answered question because the table could not be fetched
        logger.warning("genie mcp result fetch failed: %s", type(e).__name__)
        return t
    t.columns, t.rows, t.row_count, t.truncated = cols, rows, total, truncated
    return t


def _mcp_ask(w, space_id, message, conversation_id, deadline, on_conversation) -> GenieTurn:
    args = {"query": message}
    if conversation_id:
        args["conversation_id"] = conversation_id
    sc = _mcp_tool(w, space_id, "query_space", args, deadline, first=True)
    t = _mcp_turn(sc)
    _notify(on_conversation, t.conversation_id)
    while t.status != "COMPLETED":
        if t.status in TERMINAL_BAD:
            raise GenieError("failed")
        if not (t.conversation_id and t.message_id):
            raise GenieError("protocol")
        time.sleep(min(POLL_INTERVAL_S, _remaining(deadline)))
        sc = _mcp_tool(w, space_id, "poll_response",
                       {"conversation_id": t.conversation_id, "message_id": t.message_id}, deadline, first=False)
        t = _mcp_turn(sc)
    c = _content(sc)
    qa = _query_attachment(c)
    if t.sql and not (qa or {}).get("statement_response"):
        logger.warning("genie mcp completed with SQL but no statement_response (content keys=%s, query attachment "
                       "keys=%s); fetching the result through the Conversation API", _keys(c), _keys(qa))
        if t.conversation_id and t.message_id:
            t = _fetch_mcp_rows(w, space_id, t)
    elif not (t.text or t.sql or t.rows):
        logger.warning("genie mcp completed with nothing parsed (keys=%s, content keys=%s)", _keys(sc), _keys(c))
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
            (cols, rows, total, truncated), had_sr = _attachment_table(w, space_id, cid, mid, qa["attachment_id"])
            if not had_sr:
                logger.warning("genie conversation_api query result has no statement_response (attachment keys=%s)",
                               _keys(qa))
        q = (qa or {}).get("query") or {}
        t = GenieTurn(transport=TRANSPORT_CONV, conversation_id=cid, message_id=mid, status="COMPLETED",
                      text="\n\n".join(x for x in texts if x), description=q.get("description") or "",
                      sql=q.get("query"), columns=cols, rows=rows, row_count=total, truncated=truncated,
                      suggested=suggested)
        if not (t.text or t.sql or t.rows):
            logger.warning("genie conversation_api completed with nothing parsed (message keys=%s, attachment keys=%s)",
                           _keys(m), [_keys(a) for a in m.get("attachments") or []])
        return t
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

def _tagged(fn, transport: str, *args) -> GenieTurn:
    """Run one transport; any GenieError it raises is labelled with that transport (for the stream and the log)."""
    try:
        return fn(*args)
    except GenieError as e:
        if e.transport is None:
            e.transport = transport
        raise


def ask(w, message: str, conversation_id: Optional[str] = None, *, space_id: Optional[str] = None,
        deadline_s: float = DEFAULT_DEADLINE_S, transport: Optional[str] = None,
        on_conversation: Optional[Callable[[str], None]] = None) -> GenieTurn:
    """Ask the Genie space one question (or a follow-up) as whoever ``w`` authenticates as. Blocking.

    Calls ``on_conversation(conversation_id)`` as soon as the id is known. Raises ``GenieTimeout`` past the
    deadline and ``GenieError`` (safe message, ``.transport`` set) for every other failure. A fallback to the
    Conversation API uses the same ``w``.
    """
    space_id = space_id or config.GENIE_SPACE_ID
    deadline = time.monotonic() + deadline_s
    chosen = (transport or os.getenv("GENIE_TRANSPORT") or TRANSPORT_MCP).strip().lower()
    args = (w, space_id, message, conversation_id, deadline, on_conversation)
    if chosen == TRANSPORT_CONV:
        return _tagged(_conv_ask, TRANSPORT_CONV, *args)
    try:
        return _tagged(_mcp_ask, TRANSPORT_MCP, *args)
    except _McpRefused as e:
        logger.warning("genie mcp refused the first call before execution (%s); falling back to conversation_api",
                       e.kind)
        return _tagged(_conv_ask, TRANSPORT_CONV, *args)
