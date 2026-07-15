"""
routes/users.py
Endpoints for registering and listing users.
Used by the frontend to show a user picker when sending notifications.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.database import get_db
from models.orm_models import User, DeviceToken
from models.schemas import UserCreateRequest, UserOut, UsersListResponse

router = APIRouter(prefix="/users", tags=["Users"])


# ── POST /users/register ───────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user with a display name",
)
def register_user(payload: UserCreateRequest, db: Session = Depends(get_db)):
    """
    Register a user with a user_id + display name.
    If the user_id already exists the name is updated.
    """
    existing = db.query(User).filter(User.user_id == payload.user_id).first()

    if existing:
        existing.name = payload.name
        db.commit()
        db.refresh(existing)
        return existing

    user = User(user_id=payload.user_id, name=payload.name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ── GET /users ─────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=UsersListResponse,
    summary="List all registered users",
)
def list_users(db: Session = Depends(get_db)):
    """
    Returns all registered users with their user_id and name.
    Only returns users who have at least one active device token
    so the sender list only shows targetable users.
    """
    # Subquery: user_ids that have an active token
    active_user_ids = (
        db.query(DeviceToken.user_id)
        .filter(DeviceToken.is_active == True)
        .distinct()
    )

    users = (
        db.query(User)
        .filter(User.user_id.in_(active_user_ids))
        .order_by(User.name)
        .all()
    )

    return UsersListResponse(total=len(users), users=users)


# ── GET /users/all ─────────────────────────────────────────────────────────────

@router.get(
    "/all",
    response_model=UsersListResponse,
    summary="List all registered users (including those without active tokens)",
)
def list_all_users(db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.name).all()
    return UsersListResponse(total=len(users), users=users)
