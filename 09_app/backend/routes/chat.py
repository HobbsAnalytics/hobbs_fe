"""POST /api/chat: the PM's question to the Genie space, answered **as the signed-in user** (OBO) and streamed as
Server-Sent Events. Contract: 09_app/API.md, "Chat (Task 20)".

* Auth: the user's forwarded token only (``auth.user_workspace_client``). No token is a 401 JSON response, raised as a
  dependency so it is decided before the body is even validated. There is no service-principal fallback.
* Stream: every event is one ``data: <json>\\n\\n`` line, in order: status running, conversation, answer, sql, result,
  sources, status done; or status error with a safe message. While Genie is still working, ``status running`` is
  repeated every HEARTBEAT_S so idle proxies keep the stream open.
* Sources: drawing ids from a ``drawing_id`` result column are enriched with their FAIL findings from Lakebase
  (page, bbox, citation); the five code-citation labels found in the answer or the rows become ``/api/citations`` links.
* Defense in depth: a ``slip_probability`` column is removed from the result before it is emitted.
"""
import asyncio
import functools
import json
import logging
import re
import time
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from backend import auth, genie, lakebase
from backend.errors import DataUnavailable
from backend.routes.compliance import _bbox
from backend.routes.drawings import DRAWING_ID_RE

logger = logging.getLogger("bluerridge.chat")
router = APIRouter()

CHAT_TIMEOUT_S = 110.0          # wall clock for the whole Genie wait (the Apps proxy caps a request at 120 s)
HEARTBEAT_S = 15.0
MAX_MESSAGE = 2000
MAX_ROWS = 50
MAX_DRAWINGS = 10
STRIPPED_COLUMNS = {"slip_probability"}
CITATION_LABELS = ("ASME B16.5 §4.2", "OSHA 1910.147", "IBC 1005.1", "ASME B31.3 §341", "ASME B31.3 §322")
EMPTY_ANSWER = "I'm not sure which milestones you mean — try naming a discipline or specifying 'this week'."
GENERIC_ERROR = "Something went wrong while asking Genie. Try again in a moment."
FINDINGS = "bluerridge_app.compliance_findings_synced"


class ChatRequest(BaseModel):
    message: str = Field(..., max_length=MAX_MESSAGE)
    conversation_id: Optional[str] = Field(None, pattern=r"^[A-Za-z0-9_-]{1,64}$")

    @field_validator("message")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("message must not be empty")
        return v


def _user_client(request: Request):
    """Dependency: the OBO client, or a 401 before the body is looked at. Never the SP."""
    return auth.user_workspace_client(request)


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False, default=str, separators=(',', ':'))}\n\n"


# --- shaping Genie's turn into events ----------------------------------------------------------------------------

def _strip_columns(columns: list, rows: list):
    keep = [i for i, c in enumerate(columns) if str(c).lower() not in STRIPPED_COLUMNS]
    return [columns[i] for i in keep], [[r[i] if i < len(r) else None for i in keep] for r in rows]


def _drawing_ids(columns: list, rows: list) -> list:
    idx = next((i for i, c in enumerate(columns) if str(c).lower() == "drawing_id"), None)
    if idx is None:
        return []
    out = []
    for r in rows:
        v = r[idx] if idx < len(r) else None
        if isinstance(v, str) and DRAWING_ID_RE.fullmatch(v) and v not in out:
            out.append(v)
            if len(out) == MAX_DRAWINGS:
                break
    return out


def _drawing_sources(ids: list) -> list:
    if not ids:
        return []
    by_id = {i: [] for i in ids}
    try:
        rows = lakebase.query(
            f"SELECT drawing_id, finding_id, page_num, bbox, citation FROM {FINDINGS} "
            f"WHERE status = %s AND drawing_id = ANY(%s) ORDER BY drawing_id, finding_id", ("FAIL", list(ids)))
        for r in rows:
            if r.get("drawing_id") in by_id:
                by_id[r["drawing_id"]].append(r)
    except DataUnavailable:
        logger.warning("chat sources: Lakebase unavailable, drawing sources sent without findings")
    items = []
    for d in ids:
        found = by_id[d]
        if not found:
            items.append({"kind": "drawing", "drawing_id": d, "finding_id": None, "page_num": None, "bbox": None,
                          "citation": None})
        for f in found:
            items.append({"kind": "drawing", "drawing_id": d, "finding_id": f.get("finding_id"),
                          "page_num": f.get("page_num"), "bbox": _bbox(f.get("bbox")), "citation": f.get("citation")})
    return items


def _citation_sources(text: str, rows: list) -> list:
    haystack = " ".join([text or ""] + [c for r in rows for c in r if isinstance(c, str)])
    haystack = re.sub(r"§\s+", "§", re.sub(r"\s+", " ", haystack))
    return [{"kind": "citation", "label": label, "url": "/api/citations/" + quote(label, safe="")}
            for label in CITATION_LABELS if label in haystack]


def turn_events(t: genie.GenieTurn) -> list:
    """Events after ``conversation``: answer, sql, result, sources (each only when there is something to show)."""
    columns, rows = _strip_columns(t.columns, t.rows)
    has_result = bool(t.sql) and bool(columns)
    answer = t.text or (t.description if t.sql else "")
    if not answer and not t.sql and not rows:
        return [{"type": "answer", "text": EMPTY_ANSWER}]
    events = []
    if answer:
        events.append({"type": "answer", "text": answer})
    if t.sql:
        events.append({"type": "sql", "query": t.sql})
    shown = rows[:MAX_ROWS]
    if has_result:
        row_count = max(t.row_count, len(rows))
        events.append({"type": "result", "columns": columns, "rows": shown, "row_count": row_count,
                       "truncated": bool(t.truncated or row_count > len(shown))})
    items = _drawing_sources(_drawing_ids(columns, shown)) + _citation_sources(answer, shown)
    if items:
        events.append({"type": "sources", "items": items})
    return events


# --- the stream --------------------------------------------------------------------------------------------------

async def _stream(w, req: ChatRequest, email: Optional[str]):
    started = time.monotonic()
    outcome, transport, got_sql, n_rows = "error", "-", False, 0
    yield _sse({"type": "status", "value": "running"})
    loop = asyncio.get_running_loop()
    ids: asyncio.Queue = asyncio.Queue()
    job = loop.run_in_executor(None, functools.partial(
        genie.ask, w, req.message, req.conversation_id,
        on_conversation=lambda cid: loop.call_soon_threadsafe(ids.put_nowait, cid)))
    deadline = loop.time() + CHAT_TIMEOUT_S
    sent_conversation = None
    next_id = None
    try:
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise genie.GenieTimeout()
            next_id = asyncio.ensure_future(ids.get())
            done, _ = await asyncio.wait({job, next_id}, timeout=min(HEARTBEAT_S, remaining),
                                         return_when=asyncio.FIRST_COMPLETED)
            if next_id in done:
                cid = next_id.result()
                if cid and cid != sent_conversation:
                    sent_conversation = cid
                    yield _sse({"type": "conversation", "conversation_id": cid})
            else:
                next_id.cancel()
            if job in done:
                break
            if not done:
                yield _sse({"type": "status", "value": "running"})
        t = job.result()
        transport, got_sql, n_rows = t.transport, bool(t.sql), len(t.rows)
        if t.conversation_id and t.conversation_id != sent_conversation:
            yield _sse({"type": "conversation", "conversation_id": t.conversation_id})
        for event in await loop.run_in_executor(None, turn_events, t):
            yield _sse(event)
        outcome = "done"
        yield _sse({"type": "status", "value": "done"})
    except genie.GenieError as e:
        outcome = f"error:{e.kind}"
        yield _sse({"type": "status", "value": "error", "message": str(e)})
    except Exception as e:  # never a traceback or exception text in the stream or the log
        outcome = f"error:{type(e).__name__}"
        yield _sse({"type": "status", "value": "error", "message": GENERIC_ERROR})
    finally:
        if next_id is not None and not next_id.done():
            next_id.cancel()
        if not job.done():
            job.cancel()  # cannot stop the worker thread; Genie's own deadline ends it shortly
        logger.info("chat email=%s transport=%s outcome=%s got_sql=%s rows=%s elapsed_ms=%d",
                    email, transport, outcome, got_sql, n_rows, (time.monotonic() - started) * 1000)


@router.post("/chat")
def chat(req: ChatRequest, request: Request, w=Depends(_user_client)) -> StreamingResponse:
    email = auth.identity(request)["email"]
    return StreamingResponse(_stream(w, req, email), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
