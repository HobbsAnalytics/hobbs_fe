"""Drawing metadata (SQL warehouse, UC row-filtered), its findings (Lakebase) and the PDF (Volume)."""
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend import config, lakebase, volume, warehouse
from backend.routes.compliance import _bbox

router = APIRouter()

# Covers all 1,200 ids in drawing_register: BRL-<disc 3>-<type 2-4>-<4 digits>, e.g. BRL-INS-PID-0052, BRL-ELE-GA-0023.
DRAWING_ID_RE = re.compile(r"BRL-[A-Z]{3}-[A-Z]{2,4}-[0-9]{4}")
VOLUME_PREFIX = f"/Volumes/{config.CATALOG}/{config.SCHEMA_PREFIX}_landing/drawings/"
REGISTER = f"{config.CATALOG}.{config.SCHEMA_PREFIX}_gold_pm.drawing_register"


def valid_drawing_id(drawing_id: str) -> str:
    if not DRAWING_ID_RE.fullmatch(drawing_id):
        raise HTTPException(status_code=422, detail="drawing_id must look like BRL-PIP-ISO-0004")
    return drawing_id


def _register_row(drawing_id: str) -> dict:
    rows = warehouse.query(
        f"SELECT drawing_id, discipline, revision, drawing_type, volume_path, latest_review_date, latest_status, "
        f"fail_count FROM {REGISTER} WHERE drawing_id = :drawing_id", {"drawing_id": drawing_id})
    if not rows:
        raise HTTPException(status_code=404, detail="Drawing not found or not visible to the app")
    return rows[0]


@router.get("/drawings/{drawing_id}")
def drawing_detail(drawing_id: str) -> dict:
    valid_drawing_id(drawing_id)
    meta = _register_row(drawing_id)
    findings = lakebase.query(
        "SELECT drawing_id, finding_id, status, severity, citation, reason, evidence_text, page_num, bbox, bbox_source, "
        "review_date FROM bluerridge_app.compliance_findings_synced WHERE drawing_id = %s ORDER BY finding_id",
        (drawing_id,))
    return {**meta, "pdf_url": f"/api/drawings/{drawing_id}/pdf",
            "findings": [{**f, "bbox": _bbox(f["bbox"])} for f in findings]}


@router.get("/drawings/{drawing_id}/pdf")
def drawing_pdf(drawing_id: str):
    valid_drawing_id(drawing_id)
    path = _register_row(drawing_id).get("volume_path") or ""
    # The path comes from the table; still refuse anything that is not a PDF inside the drawings volume.
    if not path.startswith(VOLUME_PREFIX) or ".." in path or not path.endswith(".pdf"):
        raise HTTPException(status_code=404, detail="PDF not available for this drawing")
    try:
        stream = volume.open_pdf(path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="PDF not found in the volume") from None

    def chunks():
        try:
            while True:
                b = stream.read(65536)
                if not b:
                    break
                yield b
        finally:
            close = getattr(stream, "close", None)
            if close:
                close()

    return StreamingResponse(chunks(), media_type="application/pdf",
                             headers={"Content-Disposition": f'inline; filename="{drawing_id}.pdf"'})
