"""Request authentication (GDD §6: all endpoints require a bearer token).

Two pluggable modes:

* ``dev``      — accept ``Authorization: Bearer dev:<uid>`` and trust the uid.
                 This is what powers local anonymous play with no Firebase
                 project. The frontend generates a stable random uid and keeps
                 it in localStorage.
* ``firebase`` — verify a Firebase ID token with the Admin SDK.

Swapping modes is a config change only; the rest of the app deals in a uniform
``AuthedUser``.
"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status

from .config import Settings, get_settings

_firebase_ready = False


@dataclass
class AuthedUser:
    uid: str
    anonymous: bool = True
    display_name: str | None = None
    photo_url: str | None = None


def _parse_bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return authorization[7:].strip()


def _ensure_firebase(settings: Settings) -> None:
    global _firebase_ready
    if _firebase_ready:
        return
    import firebase_admin  # imported lazily so dev mode needs no firebase creds
    from firebase_admin import credentials

    if not firebase_admin._apps:
        if settings.firebase_credentials:
            cred = credentials.Certificate(settings.firebase_credentials)
            firebase_admin.initialize_app(cred)
        else:
            # Application Default Credentials (GOOGLE_APPLICATION_CREDENTIALS).
            firebase_admin.initialize_app()
    _firebase_ready = True


def get_current_user(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> AuthedUser:
    token = _parse_bearer(authorization)

    if settings.auth_mode == "dev":
        # Expected shape: "dev:<uid>". Anything else is rejected so a stray real
        # Firebase token can't be silently trusted.
        if not token.startswith("dev:"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="dev auth expects a 'dev:<uid>' token",
            )
        uid = token[4:].strip()
        if not uid:
            raise HTTPException(status_code=401, detail="empty uid")
        return AuthedUser(uid=uid, anonymous=True)

    # firebase mode
    _ensure_firebase(settings)
    from firebase_admin import auth as fb_auth

    try:
        decoded = fb_auth.verify_id_token(token)
    except Exception as exc:  # noqa: BLE001 - surface as 401 regardless of cause
        raise HTTPException(status_code=401, detail=f"invalid id token: {exc}") from exc

    provider = (decoded.get("firebase", {}) or {}).get("sign_in_provider")
    return AuthedUser(
        uid=decoded["uid"],
        anonymous=provider == "anonymous",
        display_name=decoded.get("name"),
        photo_url=decoded.get("picture"),
    )
