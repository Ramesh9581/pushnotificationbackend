"""
routes/devices.py
Endpoints for registering and managing web device (FCM) tokens.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.database import get_db
from models.orm_models import DeviceToken
from models.schemas import (
    DeviceRegisterRequest,
    DeviceRegisterResponse,
    DeviceTokenOut,
)

router = APIRouter(prefix="/devices", tags=["Devices"])


# ── POST /devices/register ─────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=DeviceRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a device FCM token",
)
def register_device(payload: DeviceRegisterRequest, db: Session = Depends(get_db)):
    """
    Register or refresh a web browser's FCM token.

    - If the token already exists it is marked active and user_id / device_name
      are updated (handles token refresh).
    - If a different token exists for the same user_id + platform combination
      that old token is deactivated first so each user always has one active
      token per browser session.
    """
    existing = db.query(DeviceToken).filter(DeviceToken.token == payload.token).first()

    if existing:
        # Token already known – refresh metadata
        existing.user_id     = payload.user_id
        existing.platform    = payload.platform
        existing.device_name = payload.device_name
        existing.is_active   = True
        db.commit()
        db.refresh(existing)
        return DeviceRegisterResponse(
            id=existing.id,
            user_id=existing.user_id,
            platform=existing.platform,
            device_name=existing.device_name,
            is_active=existing.is_active,
            created_at=existing.created_at,
            message="Token refreshed successfully.",
        )

    # Deactivate any previous token for this user+platform
    db.query(DeviceToken).filter(
        DeviceToken.user_id  == payload.user_id,
        DeviceToken.platform == payload.platform,
        DeviceToken.is_active == True,
    ).update({"is_active": False})

    new_token = DeviceToken(
        user_id     = payload.user_id,
        platform    = payload.platform,
        token       = payload.token,
        device_name = payload.device_name,
        is_active   = True,
    )
    db.add(new_token)
    db.commit()
    db.refresh(new_token)

    return DeviceRegisterResponse(
        id=new_token.id,
        user_id=new_token.user_id,
        platform=new_token.platform,
        device_name=new_token.device_name,
        is_active=new_token.is_active,
        created_at=new_token.created_at,
        message="Device registered successfully.",
    )


# ── GET /devices/{user_id} ─────────────────────────────────────────────────────

@router.get(
    "/{user_id}",
    response_model=list[DeviceTokenOut],
    summary="Get all active tokens for a user",
)
def get_user_devices(user_id: str, db: Session = Depends(get_db)):
    """Return all active FCM tokens registered for the given user."""
    tokens = (
        db.query(DeviceToken)
        .filter(DeviceToken.user_id == user_id, DeviceToken.is_active == True)
        .all()
    )
    return tokens


# ── DELETE /devices/{token} ────────────────────────────────────────────────────

@router.delete(
    "/{token}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate / unregister a device token",
)
def deactivate_device(token: str, db: Session = Depends(get_db)):
    """Mark a token as inactive (e.g. on user logout)."""
    device = db.query(DeviceToken).filter(DeviceToken.token == token).first()
    if not device:
        raise HTTPException(status_code=404, detail="Token not found.")
    device.is_active = False
    db.commit()
