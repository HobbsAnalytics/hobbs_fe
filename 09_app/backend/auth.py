"""Who is calling, and which Databricks identity a backend call runs as.

Two identities (research and sources: backend/AUTH_NOTES.md):

* OBO (on behalf of the signed-in PM). The Databricks Apps proxy forwards the user's short-lived OAuth token in
  ``x-forwarded-access-token`` on every request. Only the Genie chat uses it (Task 20), so Genie answers with that
  PM's own Unity Catalog permissions, including the drawing_register row filter.
* SP (the app's service principal). The platform injects DATABRICKS_HOST / DATABRICKS_CLIENT_ID /
  DATABRICKS_CLIENT_SECRET and ``WorkspaceClient()`` picks them up (OAuth M2M). Warehouse reads, Lakebase and
  Volume PDFs run as the SP.

Token hygiene: the forwarded token is read per request, passed straight to the SDK, and never stored, logged or
returned. ``identity()`` only reads headers and never constructs a client.
"""
from functools import lru_cache
from typing import Optional

from databricks.sdk import WorkspaceClient
from fastapi import HTTPException, Request

# Exact header names (Databricks Apps docs: dev-tools/databricks-apps/auth and /http-headers).
USER_TOKEN_HEADER = "x-forwarded-access-token"
EMAIL_HEADER = "x-forwarded-email"
USER_HEADER = "x-forwarded-user"
PREFERRED_USERNAME_HEADER = "x-forwarded-preferred-username"


def _header(request: Request, name: str) -> Optional[str]:
    value = request.headers.get(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def get_user_token(request: Request) -> Optional[str]:
    """The signed-in user's forwarded access token, or None (local dev, or user authorization not configured)."""
    return _header(request, USER_TOKEN_HEADER)


def user_workspace_client(request: Request) -> WorkspaceClient:
    """A WorkspaceClient that acts as the signed-in user. Build one per request; never cache it.

    Fails closed: with no forwarded token this raises a 401 rather than falling back to the service principal.
    ``auth_type="pat"`` is required because the app env also carries the SP's client id/secret, and the SDK
    refuses two auth methods without an explicit choice.
    """
    token = get_user_token(request)
    if not token:
        raise HTTPException(
            status_code=401,
            detail=(
                "User authorization required: the request has no x-forwarded-access-token header. "
                "Open the app through its Databricks Apps URL (the header is never present in local dev)."
            ),
        )
    return WorkspaceClient(token=token, auth_type="pat")


@lru_cache(maxsize=1)
def sp_workspace_client() -> WorkspaceClient:
    """The app service principal's client (SDK default auth from the injected env). One per process."""
    return WorkspaceClient()


def identity(request: Request) -> dict:
    """``{email, user_name, auth_mode}`` from the forwarded headers. Never includes the token."""
    return {
        "email": _header(request, EMAIL_HEADER),
        "user_name": _header(request, PREFERRED_USERNAME_HEADER) or _header(request, USER_HEADER),
        "auth_mode": "OBO" if get_user_token(request) else "SP",
    }
