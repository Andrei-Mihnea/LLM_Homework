from typing import Optional
from flask import request
from smart_librarian.utils.jwt_helper import verify_jwt

COOKIE_NAME = "access_token"

def current_user() -> Optional[str]:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    data = verify_jwt(token)
    if not data:
        return None
    return data.get("sub")  # the username we set as subject
