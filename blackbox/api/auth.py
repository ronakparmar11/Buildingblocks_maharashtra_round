import base64
import hashlib
import hmac
import json
import time

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from blackbox.config import get_settings

router = APIRouter(prefix="/auth")
COOKIE_NAME = "blackbox_demo_session"
SESSION_TTL_SECONDS = 12 * 60 * 60


class LoginRequest(BaseModel):
    email: str
    password: str


class SessionResponse(BaseModel):
    authenticated: bool
    email: str


def _signature(payload: str) -> str:
    secret = get_settings().DEMO_AUTH_SECRET.encode()
    return hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()


def _create_token(email: str) -> str:
    payload = json.dumps(
        {"email": email, "expires": int(time.time()) + SESSION_TTL_SECONDS},
        separators=(",", ":"),
    )
    encoded = base64.urlsafe_b64encode(payload.encode()).decode()
    return f"{encoded}.{_signature(encoded)}"


def authenticated_email(request: Request) -> str | None:
    token = request.cookies.get(COOKIE_NAME, "")
    try:
        encoded, signature = token.rsplit(".", 1)
        if not hmac.compare_digest(signature, _signature(encoded)):
            return None
        payload = json.loads(base64.urlsafe_b64decode(encoded).decode())
        if int(payload["expires"]) < int(time.time()):
            return None
        return str(payload["email"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


@router.post("/login", response_model=SessionResponse)
def login(credentials: LoginRequest, response: Response) -> SessionResponse:
    settings = get_settings()
    email_matches = hmac.compare_digest(credentials.email, settings.DEMO_AUTH_EMAIL)
    password_matches = hmac.compare_digest(
        credentials.password, settings.DEMO_AUTH_PASSWORD
    )
    if not email_matches or not password_matches:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    response.set_cookie(
        COOKIE_NAME,
        _create_token(credentials.email),
        httponly=True,
        max_age=SESSION_TTL_SECONDS,
        samesite="lax",
        secure=False,
    )
    return SessionResponse(authenticated=True, email=credentials.email)


@router.get("/session", response_model=SessionResponse)
def session(request: Request) -> SessionResponse:
    email = authenticated_email(request)
    if email is None:
        raise HTTPException(status_code=401, detail="Not signed in")
    return SessionResponse(authenticated=True, email=email)


@router.post("/logout", status_code=204)
def logout(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME)