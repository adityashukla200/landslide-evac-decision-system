"""Authentication & Authorization endpoints for Officers."""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.db.models import Officer
from backend.app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    OfficerProfile,
    AuthMessage,
)
from backend.app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    check_login_rate_limit,
    record_login_failure,
    reset_login_rate_limit,
    get_current_officer,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

router = APIRouter(prefix="/auth", tags=["Officer Authentication"])


@router.post("/login", response_model=TokenResponse)
def login_officer(
    credentials: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Authenticate officer via email or phone + password.
    
    Issues short-lived JWT access token and refresh token with rate-limiting.
    """
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_key = f"login:{client_ip}:{credentials.username.strip().lower()}"

    # 1. Brute-Force Rate Limiting
    check_login_rate_limit(rate_limit_key)

    username_clean = credentials.username.strip()

    # 2. Lookup Officer by Email or Phone
    officer = db.query(Officer).filter(
        (Officer.email.ilike(username_clean)) | (Officer.phone == username_clean)
    ).first()

    if not officer or not verify_password(credentials.password, officer.password_hash):
        record_login_failure(rate_limit_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email/phone or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not officer.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Officer account has been deactivated. Please contact the District Magistrate.",
        )

    # 3. Successful authentication: reset rate limit & update last login
    reset_login_rate_limit(rate_limit_key)
    officer.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(officer)

    # 4. Generate Tokens
    token_claims = {
        "sub": officer.id,
        "name": officer.name,
        "role": officer.role,
        "district": officer.district,
        "email": officer.email,
    }
    access_token = create_access_token(token_claims)
    refresh_token = create_refresh_token({"sub": officer.id})

    # 5. Set HttpOnly Cookie for secure refresh flow
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        secure=False,  # Set to True in production HTTPS
        max_age=7 * 24 * 3600,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        officer=OfficerProfile.model_validate(officer),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    request: Request,
    response: Response,
    payload: Optional[RefreshRequest] = None,
    db: Session = Depends(get_db),
):
    """Silently issue a new access token using a valid refresh token."""
    raw_token = None
    if payload and payload.refresh_token:
        raw_token = payload.refresh_token
    elif "refresh_token" in request.cookies:
        raw_token = request.cookies.get("refresh_token")

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = decode_token(raw_token, expected_type="refresh")
    officer_id = token_data.get("sub")

    officer = db.query(Officer).filter(Officer.id == officer_id).first()
    if not officer or not officer.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Officer account not found or deactivated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    new_claims = {
        "sub": officer.id,
        "name": officer.name,
        "role": officer.role,
        "district": officer.district,
        "email": officer.email,
    }
    new_access_token = create_access_token(new_claims)
    new_refresh_token = create_refresh_token({"sub": officer.id})

    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=7 * 24 * 3600,
    )

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        officer=OfficerProfile.model_validate(officer),
    )


@router.post("/logout", response_model=AuthMessage)
def logout_officer(response: Response):
    """Clear session refresh cookie and log out."""
    response.delete_cookie(key="refresh_token")
    return AuthMessage(status="success", message="Successfully logged out.")


@router.get("/me", response_model=OfficerProfile)
def get_current_officer_profile(
    current_officer: Officer = Depends(get_current_officer),
):
    """Return the profile of the currently authenticated officer."""
    return OfficerProfile.model_validate(current_officer)
