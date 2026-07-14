from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from app_config.settings import settings
from infra.db import get_db_connection

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _require_jwt_secret() -> str:
    if not settings.jwt_secret_key:
        raise RuntimeError("JWT_SECRET_KEY is required. Add it to agent/.env before starting the API.")
    return settings.jwt_secret_key


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(user: dict[str, Any]) -> str:
    expires_at = _utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {
        "sub": user["user_id"],
        "username": user["username"],
        "type": "access",
        "exp": expires_at,
    }
    return jwt.encode(payload, _require_jwt_secret(), algorithm=ALGORITHM)


def create_refresh_token(user_id: str) -> tuple[str, datetime]:
    token = secrets.token_urlsafe(48)
    expires_at = _utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days)
    token_hash = hash_refresh_token(token)
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO refresh_tokens (token_hash, user_id, expires_at)
                VALUES (%s, %s, %s)
                """,
                (token_hash, user_id, expires_at.replace(tzinfo=None)),
            )
    return token, expires_at


def authenticate_user(username: str, password: str) -> dict[str, Any] | None:
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT user_id, username, display_name, password_hash, disabled
                FROM users
                WHERE username = %s
                LIMIT 1
                """,
                (username,),
            )
            user = cursor.fetchone()
    if not user or user["disabled"] or not verify_password(password, user["password_hash"]):
        return None
    return user


def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT user_id, username, display_name, disabled
                FROM users
                WHERE user_id = %s
                LIMIT 1
                """,
                (user_id,),
            )
            user = cursor.fetchone()
    if not user or user["disabled"]:
        return None
    return user


def issue_token_pair(user: dict[str, Any]) -> dict[str, Any]:
    refresh_token, refresh_expires_at = create_refresh_token(user["user_id"])
    return {
        "access_token": create_access_token(user),
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_token_expire_minutes * 60,
        "refresh_expires_at": refresh_expires_at.isoformat(),
        "user": public_user(user),
    }


def refresh_token_pair(refresh_token: str) -> dict[str, Any]:
    token_hash = hash_refresh_token(refresh_token)
    now = _utcnow().replace(tzinfo=None)
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT token_hash, user_id, expires_at, revoked_at
                FROM refresh_tokens
                WHERE token_hash = %s
                LIMIT 1
                """,
                (token_hash,),
            )
            token_row = cursor.fetchone()
            if not token_row or token_row["revoked_at"] or token_row["expires_at"] <= now:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

            cursor.execute(
                "UPDATE refresh_tokens SET revoked_at = NOW() WHERE token_hash = %s",
                (token_hash,),
            )
            cursor.execute(
                """
                SELECT user_id, username, display_name, disabled
                FROM users
                WHERE user_id = %s
                LIMIT 1
                """,
                (token_row["user_id"],),
            )
            user = cursor.fetchone()
    if not user or user["disabled"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    return issue_token_pair(user)


def revoke_refresh_token(refresh_token: str) -> None:
    token_hash = hash_refresh_token(refresh_token)
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE refresh_tokens SET revoked_at = NOW() WHERE token_hash = %s AND revoked_at IS NULL",
                (token_hash,),
            )


def public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "display_name": user.get("display_name") or user["username"],
    }


def get_current_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, _require_jwt_secret(), algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    user = get_user_by_id(str(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is disabled or missing")
    return user


CurrentUser = Depends(get_current_user)
