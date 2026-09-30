"""Pydantic schemas for Officer Authentication & RBAC."""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class LoginRequest(BaseModel):
    """Credentials payload for officer authentication."""

    username: str = Field(..., min_length=3, description="Officer official email address or phone number")
    password: str = Field(..., min_length=4, description="Plaintext password for verification")


class OfficerProfile(BaseModel):
    """Public profile of an authenticated officer."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    district: str = "Uttarkashi"
    email: str
    phone: Optional[str] = None
    role: str = "officer"  # officer, admin
    designation: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None


class TokenResponse(BaseModel):
    """JWT Bearer tokens issued upon successful login or refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(1800, description="Access token expiration window in seconds (30 mins)")
    officer: OfficerProfile


class RefreshRequest(BaseModel):
    """Refresh token payload."""

    refresh_token: Optional[str] = Field(None, description="Active refresh token string")


class AuthMessage(BaseModel):
    """Generic status response message."""

    status: str = "success"
    message: str
