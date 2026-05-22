from typing import Literal

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_user
from app.core.config import settings
from app.core.limiter import limiter
from app.db.session import get_db
from app.middleware.exceptions import BusinessError
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    SignupRequest,
    TokenResponse,
    UserDTO,
)
from app.services import auth_service

_COOKIE_NAME = "refresh_token"
_COOKIE_MAX_AGE = 14 * 24 * 60 * 60  # 14 days


def _set_refresh_cookie(response: Response, raw: str) -> None:
    # In production the api and web run on separate domains, so the refresh
    # request is cross-site and the cookie must be SameSite=None to be sent.
    # Locally the Vite proxy keeps everything same-origin, so Strict holds.
    samesite: Literal["none", "strict"] = (
        "none" if settings.ENVIRONMENT == "production" else "strict"
    )
    response.set_cookie(
        key=_COOKIE_NAME,
        value=raw,
        httponly=True,
        secure=True,
        samesite=samesite,
        path="/v1/auth",
        max_age=_COOKIE_MAX_AGE,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=_COOKIE_NAME, path="/v1/auth")


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", status_code=201)
@limiter.limit("10/5minute")
async def signup(
    request: Request,
    body: SignupRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:  # type: ignore[type-arg]
    user, access, refresh = await auth_service.signup(
        db, email=body.email, name=body.name, password=body.password
    )
    _set_refresh_cookie(response, refresh)
    return {
        "user": UserDTO.model_validate(user),
        "access_token": access,
        "token_type": "bearer",
    }


@router.post("/login")
@limiter.limit("10/5minute")
async def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    _user, access, refresh = await auth_service.login(
        db, email=body.email, password=body.password
    )
    _set_refresh_cookie(response, refresh)
    return TokenResponse(access_token=access)


@router.post("/refresh")
@limiter.limit("30/5minute")
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    raw = request.cookies.get(_COOKIE_NAME)
    if not raw:
        raise BusinessError(
            "REFRESH_MISSING", "Refresh token cookie missing", status_code=401
        )
    access, new_raw = await auth_service.rotate_refresh(db, raw)
    _set_refresh_cookie(response, new_raw)
    return TokenResponse(access_token=access)


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> None:
    raw = request.cookies.get(_COOKIE_NAME)
    if raw:
        await auth_service.logout(db, raw)
    _clear_refresh_cookie(response)


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)) -> UserDTO:
    return UserDTO.model_validate(current_user)


@router.post("/change-password", status_code=204)
async def change_password(
    body: ChangePasswordRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    await auth_service.change_password(
        db,
        user=current_user,
        current_password=body.current_password,
        new_password=body.new_password,
    )
    _clear_refresh_cookie(response)
