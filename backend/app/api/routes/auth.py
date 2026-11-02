from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.security import create_access_token, hash_password, verify_password
from app.db.database import get_db
from app.db.models.user import ALL_ROLES, User
from app.schemas.auth import LoginRequest, TokenResponse, UserCreate, UserOut, UserRoleUpdate

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is disabled")
    token = create_access_token(user.id, user.role)
    return TokenResponse(access_token=token, role=user.role, full_name=user.full_name, email=user.email)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.post("/users", response_model=UserOut)
def create_user(payload: UserCreate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    if payload.role not in ALL_ROLES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid role. Must be one of {ALL_ROLES}")
    if db.query(User).filter(User.email == payload.email.lower()).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A user with this email already exists")
    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}/role", response_model=UserOut)
def update_user_role(
    user_id: str, payload: UserRoleUpdate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)
):
    if payload.role not in ALL_ROLES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid role. Must be one of {ALL_ROLES}")
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    user.role = payload.role
    db.commit()
    db.refresh(user)
    return user
