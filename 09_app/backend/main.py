"""Blue Ridge LNG Project Co-Pilot - FastAPI entrypoint.

Serves the JSON API under /api, /health, and the built React SPA (static assets
plus an index.html fallback for client-side routes).
"""
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from backend import config


def create_app(static_dir: Optional[Path] = None) -> FastAPI:
    static_root = Path(static_dir) if static_dir is not None else config.STATIC_DIR
    app = FastAPI(title="Blue Ridge LNG Project Co-Pilot")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    # Feature routers (Tasks 18-20) are included here, before the SPA catch-all:
    # from backend.routes import ...; app.include_router(..., prefix="/api")

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
