"""auth API — inbound adapter (FastAPI). Depends only on application services."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.common.result import Err, Result
from app.core.container import Container
from app.core.exceptions.taxonomy import http_status_for
from app.core.logging.setup import get_logger
from app.modules.auth.presentation.schemas import (
    ApiKeyRequest,
    ApiKeyResponse,
    ApiKeySecretResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.modules.auth.application.services import ApiKeyService, AuthService
from app.modules.auth.domain.entities import Role, TokenClaims, User
from app.modules.auth.domain.ports import UserRepository

logger = get_logger("auth.presentation")
router = APIRouter(prefix="/auth", tags=["auth"])


def _container(request: Request) -> Container:
    return request.app.state.container


def _auth_service(request: Request) -> AuthService:
    return _container(request).resolve(AuthService)


def _api_key_service(request: Request) -> ApiKeyService:
    return _container(request).resolve(ApiKeyService)


def _or_http(result: Result, status_override: int | None = None) -> None:
    if isinstance(result, Err):
        raise HTTPException(
            status_code=status_override or http_status_for(result.error_value),
            detail=result.error_value.message,
        )


async def get_current_claims(request: Request) -> TokenClaims:
    auth_header = request.headers.get("Authorization", "")
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="missing_token")
    result = await _auth_service(request).verify_access(token)
    if isinstance(result, Err):
        raise HTTPException(status_code=401, detail=result.error_value.message)
    return result.ok_value()


async def get_current_user(request: Request, claims: Annotated[TokenClaims, Depends(get_current_claims)]) -> User:
    users: UserRepository = _container(request).resolve(UserRepository)
    user = await users.get_by_id(claims.subject)
    if user is None or user.disabled:
        raise HTTPException(status_code=401, detail="user_disabled")
    return user


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, request: Request) -> TokenResponse:
    role = Role(body.role) if body.role in (Role.VIEWER.value, Role.ANALYST.value) else Role.VIEWER
    result = await _auth_service(request).register(username=body.username, password=body.password, role=role)
    _or_http(result, 400)
    token = await _auth_service(request).login(username=body.username, password=body.password)
    _or_http(token, 401)
    return TokenResponse(**token.ok_value().__dict__)


@router.post("/token", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request) -> TokenResponse:
    result = await _auth_service(request).login(username=body.username, password=body.password)
    _or_http(result, 401)
    return TokenResponse(**result.ok_value().__dict__)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, request: Request) -> TokenResponse:
    result = await _auth_service(request).refresh(body.refresh_token)
    _or_http(result, 401)
    return TokenResponse(**result.ok_value().__dict__)


@router.post("/api-keys", response_model=ApiKeySecretResponse, status_code=201)
async def create_api_key(
    body: ApiKeyRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
) -> ApiKeySecretResponse:
    result = await _api_key_service(request).create(user.id, label=body.label)
    _or_http(result)
    key, secret = result.ok_value()
    return ApiKeySecretResponse(
        key_id=str(key.id),
        key_prefix=key.key_prefix,
        created_at=key.created_at.isoformat(),
        secret=secret,
    )


@router.get("/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys(request: Request, user: Annotated[User, Depends(get_current_user)]) -> list[ApiKeyResponse]:
    keys = await _api_key_service(request).list(user.id)
    return [
        ApiKeyResponse(
            key_id=str(k.id),
            key_prefix=k.key_prefix,
            created_at=k.created_at.isoformat(),
        )
        for k in keys
    ]
