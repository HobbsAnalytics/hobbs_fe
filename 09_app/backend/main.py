"""Blue Ridge LNG Project Co-Pilot - FastAPI entrypoint.

Serves the JSON API under /api, /health, and the built React SPA (static assets
plus an index.html fallback for client-side routes).
"""
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from backend import config, selftest
from backend.errors import install_error_handlers
from backend.routes import chat, citations, compliance, drawings, kpi, whoami


def _configure_app_logging() -> None:
    """Send the app's own INFO lines (logger "bluerridge.*") to stdout, which `databricks apps logs` captures.

    Only this namespace is raised to INFO, so third-party loggers keep their defaults. App code logs who and how
    (email, auth_mode), never a token.
    """
    log = logging.getLogger("bluerridge")
    if not log.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
        log.addHandler(handler)
    log.setLevel(logging.INFO)


def create_app(static_dir: Optional[Path] = None) -> FastAPI:
    _configure_app_logging()
    static_root = Path(static_dir) if static_dir is not None else config.STATIC_DIR

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        # Non-blocking: SP data access is proven in the logs (one line per source), never at the cost of startup.
        if os.getenv("BLUERRIDGE_SELFTEST", "on").lower() != "off":
            selftest.start_background()
        yield

    app = FastAPI(title="Blue Ridge LNG Project Co-Pilot", lifespan=lifespan)
    install_error_handlers(app)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    # Feature routers (Tasks 18-20) are included here, before the SPA catch-all.
    app.include_router(whoami.router, prefix="/api")
    for r in (kpi.router, compliance.router, drawings.router, citations.router, chat.router):
        app.include_router(r, prefix="/api")

    index_file = static_root / "index.html"

    # Registered last so /health and /api/* routes keep priority.
    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        if full_path:
            candidate = (static_root / full_path).resolve()
            if static_root.resolve() in candidate.parents and candidate.is_file():
                return FileResponse(candidate)
        if index_file.is_file():
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail="Frontend build not found; run `npm run build`")

    return app


app = create_app()
