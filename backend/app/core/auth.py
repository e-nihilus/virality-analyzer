"""Authentication dependency — placeholder for future Clerk JWT integration.

When `settings.auth_enabled` is True, this will validate Bearer tokens
from Clerk and extract user_id. For now, it returns None (anonymous).
"""

from __future__ import annotations

from fastapi import Request

from .config import settings


async def get_current_user_id(request: Request) -> str | None:
    """Extract user_id from the request.

    - auth_enabled=False → returns None (local/dev mode).
    - auth_enabled=True  → will validate Clerk JWT and return user_id.
    """
    if not settings.auth_enabled:
        return None

    # TODO: Implement Clerk JWT validation when integrating into AureaSuite
    # 1. Extract Bearer token from Authorization header
    # 2. Verify with Clerk's JWKS endpoint
    # 3. Return clerk_user_id from token claims
    raise NotImplementedError(
        "Auth is enabled but Clerk JWT validation is not yet implemented. "
        "Set AUREA_AUTH_ENABLED=false for local development."
    )
