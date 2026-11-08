"""GET /api/whoami: who the app thinks is calling, and whether a user token was forwarded (OBO) or not (SP)."""
import logging

from fastapi import APIRouter, Request

from backend.auth import identity

logger = logging.getLogger("bluerridge.auth")

router = APIRouter()


@router.get("/whoami")
def whoami(request: Request) -> dict:
    who = identity(request)
    # Request log: who and how only. The forwarded token is never logged or returned.
    logger.info("whoami email=%s auth_mode=%s", who["email"], who["auth_mode"])
    return who
