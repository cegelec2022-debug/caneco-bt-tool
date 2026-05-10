from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.models.user import UserRole
from app.repositories import user_repository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse

_VALID_ROLES = {UserRole.BE, UserRole.CHEF_CHANTIER, UserRole.RA, UserRole.ADMIN}


def login(db: Session, payload: LoginRequest) -> TokenResponse:
    user = user_repository.get_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants invalides.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé.",
        )
    return TokenResponse(access_token=create_access_token(subject=user.id))


def register(db: Session, payload: RegisterRequest) -> TokenResponse:
    if payload.role not in _VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Rôle invalide. Valeurs acceptées : {sorted(_VALID_ROLES)}",
        )
    if user_repository.get_by_email(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un compte existe déjà avec cet email.",
        )
    user = user_repository.create(
        db,
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        role=payload.role,
    )
    return TokenResponse(access_token=create_access_token(subject=user.id))
