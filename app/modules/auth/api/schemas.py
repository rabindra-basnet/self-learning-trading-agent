"""auth API schemas (transport contracts — never leak provider types)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=256)
    role: str = "viewer"


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_sec: int


class ApiKeyResponse(BaseModel):
    key_id: str
    key_prefix: str
    created_at: str


class ApiKeySecretResponse(ApiKeyResponse):
    secret: str


class ApiKeyRequest(BaseModel):
    label: str = Field(min_length=1, max_length=64)
