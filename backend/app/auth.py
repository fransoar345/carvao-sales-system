import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Iterable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session, joinedload

from .config import get_settings
from .database import get_db
from . import models


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 240_000)
    return f"pbkdf2_sha256${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt_b64, digest_b64 = stored.split("$", 2)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
    except ValueError:
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 240_000)
    return hmac.compare_digest(actual, expected)


def create_access_token(user: models.User) -> str:
    settings = get_settings()
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user.id), "role": user.role, "name": user.name, "exp": expires}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = int(payload["sub"])
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido") from exc
    user = db.query(models.User).options(joinedload(models.User.access_roles).joinedload(models.AccessRole.permissions), joinedload(models.User.permission_overrides).joinedload(models.UserPermissionOverride.permission)).filter(models.User.id == user_id).first()
    if not user or not user.active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inativo")
    return user


def permission_codes(user: models.User) -> set[str]:
    codes = {permission.code for role in user.access_roles if role.active for permission in role.permissions}
    for override in user.permission_overrides:
        if override.allowed:
            codes.add(override.permission.code)
        else:
            codes.discard(override.permission.code)
    return codes


def has_permission(user: models.User, code: str) -> bool:
    return code in permission_codes(user)


def require_permission(*codes: str, match_all: bool = True):
    def checker(user: models.User = Depends(get_current_user)) -> models.User:
        granted = permission_codes(user)
        allowed = all(code in granted for code in codes) if match_all else any(code in granted for code in codes)
        if not allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permissao insuficiente")
        return user
    return checker


def require_roles(*roles: str):
    def checker(user: models.User = Depends(get_current_user)) -> models.User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
        return user

    return checker


def can_manage(user: models.User, roles: Iterable[str]) -> bool:
    return user.role in set(roles)
