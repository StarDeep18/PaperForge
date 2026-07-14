"""
PaperForge Security Utilities.

Auth-ready security module. Currently provides a default development user.
Designed to be extended with JWT validation, OAuth2, or external auth providers.
"""

from datetime import datetime, timezone


# Default development user — replaced by real auth in production
DEFAULT_USER_ID = "dev-user-001"
DEFAULT_USER_EMAIL = "dev@paperforge.local"
DEFAULT_USER_NAME = "Developer"


def get_current_user_id() -> str:
    """
    Return the current authenticated user's ID.

    In development mode, returns a default user ID.
    In production, this will validate JWT tokens and extract the user ID.
    """
    return DEFAULT_USER_ID


def utc_now() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)
