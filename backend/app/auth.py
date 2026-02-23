"""
Blueprint Backend — Auth Helpers

Placeholder for V0 (anonymous). When auth is added (V1), this module
will provide get_current_user_id() from JWT/session.
"""

from fastapi import Request


def get_current_user_id(request: Request) -> str | None:
    """
    Return the authenticated user's ID, or None if anonymous.

    V0: Always returns None (no auth).
    V1: Read from Supabase Auth JWT, session cookie, or Authorization header.
    """
    # TODO: When auth is added, extract user_id from:
    # - Authorization: Bearer <jwt> (Supabase Auth)
    # - Or session cookie that maps to auth.users
    return None
