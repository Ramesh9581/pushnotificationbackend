"""
routes/notifications.py
Endpoint to send a push notification to all active devices of a user.
Protected by a simple API-Key header.
"""

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from config import settings
from db.database import get_db
from models.orm_models import DeviceToken, NotificationLog
from models.schemas import (
    SendNotificationRequest,
    SendNotificationResponse,
    SendNotificationResult,
)
from services.firebase_service import send_fcm_notification

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ── API-key guard ──────────────────────────────────────────────────────────────

def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """Dependency that validates the X-API-Key header."""
    if settings.API_KEY and x_api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )
    return x_api_key


# ── POST /notifications/send ───────────────────────────────────────────────────

@router.post(
    "/send",
    response_model=SendNotificationResponse,
    summary="Send push notification to a user's devices",
)
def send_notification(
    payload: SendNotificationRequest,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """
    Sends a push notification to **all active web tokens** registered for
    `user_id`.

    Each send attempt is logged to `notification_logs` with status
    **sent** or **failed**.

    ### Payload example
    ```json
    {
      "user_id":     "user_42",
      "title":       "New Order",
      "message":     "Your order #123 has been confirmed.",
      "screen_name": "OrderDetail",
      "data":        { "order_id": "123" }
    }
    ```
    """
    # 1. Fetch active tokens for this user
    tokens = (
        db.query(DeviceToken)
        .filter(
            DeviceToken.user_id  == payload.user_id,
            DeviceToken.is_active == True,
        )
        .all()
    )

    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active device tokens found for user '{payload.user_id}'.",
        )

    results: list[SendNotificationResult] = []
    sent_count   = 0
    failed_count = 0

    for device in tokens:
        # 2. Send via Firebase — pass platform so the right FCM config is used
        fcm_result = send_fcm_notification(
            token       = device.token,
            title       = payload.title,
            body        = payload.message,
            screen_name = payload.screen_name,
            extra_data  = payload.data,
            platform    = device.platform,
        )

        success = fcm_result.get("success", False)
        error   = fcm_result.get("error")

        if success:
            sent_count += 1
        else:
            failed_count += 1
            # Auto-deactivate unregistered tokens
            if error and "unregistered" in error.lower():
                device.is_active = False

        # 3. Write log entry
        log = NotificationLog(
            user_id       = payload.user_id,
            title         = payload.title,
            message       = payload.message,
            screen_name   = payload.screen_name,
            data          = payload.data,
            token         = device.token,
            status        = "sent" if success else "failed",
            error_message = error,
        )
        db.add(log)

        results.append(
            SendNotificationResult(
                token  = device.token[:20] + "…",   # truncate for response safety
                status = "sent" if success else "failed",
                error  = error,
            )
        )

    db.commit()

    return SendNotificationResponse(
        user_id = payload.user_id,
        total   = len(tokens),
        sent    = sent_count,
        failed  = failed_count,
        results = results,
    )
