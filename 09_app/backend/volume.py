"""Drawing PDFs from the UC Volume via the SP's Files API. Callers pass a path read from drawing_register, never user input."""
import logging
from typing import BinaryIO, Tuple

from databricks.sdk.errors import NotFound

from backend.auth import sp_workspace_client
from backend.errors import DataUnavailable

logger = logging.getLogger("bluerridge.volume")


def open_pdf(path: str) -> BinaryIO:
    try:
        return sp_workspace_client().files.download(path).contents
    except NotFound:
        raise FileNotFoundError(path) from None
    except Exception as e:
        logger.warning("volume download failed: %s", type(e).__name__)
        raise DataUnavailable(f"Volume read failed ({type(e).__name__})") from None


def stat(path: str) -> Tuple[bool, int]:
    """(exists, size in bytes)."""
    try:
        meta = sp_workspace_client().files.get_metadata(path)
        return True, int(meta.content_length or 0)
    except NotFound:
        return False, 0
