from fastapi import Header, HTTPException
from admin_panel.backend.core.config import settings

def admin_auth(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(401, "Authorization header missing")

    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid authorization format")

    token = authorization.replace("Bearer ", "")
    if token != settings.ADMIN_TOKEN:
        raise HTTPException(401, "Invalid token")

    return token