import os
import time
import jwt
from typing import Optional, Dict, Any

JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-prod")
JWT_ALGO = "HS256"
JWT_EXPIRES_MIN = int(os.getenv("JWT_EXPIRES_MIN", "30"))

def create_jwt(payload: Dict[str, Any]) -> str:
    now = int(time.time())
    exp = now + JWT_EXPIRES_MIN * 60
    body = {"iat": now, "exp": exp, **payload}
    return jwt.encode(body, JWT_SECRET, algorithm=JWT_ALGO)

def verify_jwt(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None