"""Code citation lookup: exact label match plus up to 3 related clauses (Vector Search, SQL fallback)."""
from fastapi import APIRouter, HTTPException

from backend import vector_search

router = APIRouter()
MAX_LABEL = 120


@router.get("/citations/{label}")
def citation(label: str) -> dict:
    # Starlette has already URL-decoded the path segment.
    if not label.strip() or len(label) > MAX_LABEL or not label.isprintable():
        raise HTTPException(status_code=422, detail="Invalid citation label")
    hit = vector_search.exact(label)
    if hit is None:
        raise HTTPException(status_code=404, detail="Unknown citation label")
    return {**hit, "related": vector_search.related(label, hit.get("text") or label, 3)[:3]}
