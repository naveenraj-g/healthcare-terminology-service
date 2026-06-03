from fastapi import Request


async def user_context_middleware(request: Request, call_next):
    """Populate request.state.user from X-Org-ID / X-User-ID headers.

    Org-concept endpoints require an org context. Pass X-Org-ID and X-User-ID
    headers in requests. When JWT auth is added later, replace this middleware
    with a proper token-verification middleware that populates the same keys.
    """
    request.state.user = {
        "activeOrganizationId": request.headers.get("X-Org-ID"),
        "sub": request.headers.get("X-User-ID"),
    }
    return await call_next(request)
