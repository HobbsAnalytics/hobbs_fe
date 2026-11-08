"""One error shape for the whole API: ``{"error": <short code>, "detail": <human message>}``. Never a traceback."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("bluerridge.api")


class DataUnavailable(Exception):
    """A backing store (Lakebase, SQL warehouse, Volume, Vector Search) could not be reached or refused the query.

    The message is shown to the client, so it must be safe: no SQL, no host names, no credentials.
    """


_CODES = {401: "unauthorized", 403: "forbidden", 404: "not_found", 422: "invalid_request", 503: "unavailable"}


def _body(status: int, detail) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": _CODES.get(status, "error"), "detail": detail})


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        return _body(exc.status_code, exc.detail if isinstance(exc.detail, str) else "Request failed")

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        fields = ", ".join(".".join(str(p) for p in e.get("loc", ())[1:]) or "request" for e in exc.errors())
        return _body(422, f"Invalid request parameters: {fields}")

    @app.exception_handler(DataUnavailable)
    async def _unavailable(_: Request, exc: DataUnavailable):
        return _body(503, str(exc) or "A backing data source is unavailable; try again shortly.")

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception):
        # Class name only in the log (messages can carry SQL or hosts); the client gets a generic body.
        logger.error("unhandled %s on %s", type(exc).__name__, request.url.path)
        return _body(500, "Internal error")
