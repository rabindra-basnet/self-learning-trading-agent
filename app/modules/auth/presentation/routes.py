"""auth API — inbound adapter (FastAPI). Depends only on application services."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from magic_di.fastapi import Provide

from app.core.common.result import Result
from app.core.exceptions.taxonomy import DomainError, http_status_for
from app.core.logging.setup import get_logger
from app.modules.auth.application.services import ApiKeyService, AuthService, CurrentUserService
from app.modules.auth.domain.entities import Role, User
from app.modules.auth.domain.ports import UserRepository
from app.modules.auth.presentation.schemas import (
    ApiKeyRequest,
    ApiKeyResponse,
    ApiKeySecretResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)

logger = get_logger("auth.presentation")
router = APIRouter(prefix="/auth", tags=["auth"])


def _or_http(result: Result[object, DomainError], status_override: int | None = None) -> None:
    if result.is_err:
        error = result.error_value()
        raise HTTPException(
            status_code=status_override or http_status_for(error),
            detail=error.message,
        )


async def get_current_user(
    request: Request,
    current_user: Provide[CurrentUserService],
) -> User:
    auth_header = request.headers.get("Authorization", "")
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="missing_token")
    result = await current_user.resolve(token)
    if result.is_err:
        raise HTTPException(status_code=401, detail=result.error_value().message)
    return result.ok_value()


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, auth_service: Provide[AuthService]) -> TokenResponse:
    role = Role(body.role) if body.role in (Role.VIEWER.value, Role.ANALYST.value) else Role.VIEWER
    result = await auth_service.register(username=body.username, password=body.password, role=role)
    _or_http(result, 400)
    token = await auth_service.login(username=body.username, password=body.password)
    _or_http(token, 401)
    return TokenResponse(**token.ok_value().__dict__)


@router.post("/token", response_model=TokenResponse)
async def login(body: LoginRequest, auth_service: Provide[AuthService]) -> TokenResponse:
    result = await auth_service.login(username=body.username, password=body.password)
    _or_http(result, 401)
    return TokenResponse(**result.ok_value().__dict__)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, auth_service: Provide[AuthService]) -> TokenResponse:
    result = await auth_service.refresh(body.refresh_token)
    _or_http(result, 401)
    return TokenResponse(**result.ok_value().__dict__)


@router.post("/api-keys", response_model=ApiKeySecretResponse, status_code=201)
async def create_api_key(
    body: ApiKeyRequest,
    api_key_service: Provide[ApiKeyService],
    user: Annotated[User, Depends(get_current_user)],
) -> ApiKeySecretResponse:
    result = await api_key_service.create(user.id, label=body.label)
    _or_http(result)
    key, secret = result.ok_value()
    return ApiKeySecretResponse(
        key_id=str(key.id),
        key_prefix=key.key_prefix,
        created_at=key.created_at.isoformat(),
        secret=secret,
    )


@router.get("/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys(
    api_key_service: Provide[ApiKeyService], user: Annotated[User, Depends(get_current_user)]
) -> list[ApiKeyResponse]:
    keys = await api_key_service.list(user.id)
    return [
        ApiKeyResponse(
            key_id=str(k.id),
            key_prefix=k.key_prefix,
            created_at=k.created_at.isoformat(),
        )
        for k in keys
    ]
