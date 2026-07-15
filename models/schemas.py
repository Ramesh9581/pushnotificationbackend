"""
models/schemas.py
Pydantic v2 request/response schemas for all API endpoints.
"""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


# ── Device Registration ────────────────────────────────────────────────────────

class DeviceRegisterRequest(BaseModel):
    user_id:     str  = Field(..., description="Unique identifier for the user")
    token:       str  = Field(..., description="FCM registration token from the browser")
    platform:    str  = Field(default="web", description="Platform: web | android | ios")
    device_name: Optional[str] = Field(default=None, description="Human-readable device label")


class DeviceRegisterResponse(BaseModel):
    id:          UUID
    user_id:     str
    platform:    str
    device_name: Optional[str]
    is_active:   bool
    created_at:  datetime
    message:     str


class DeviceTokenOut(BaseModel):
    id:          UUID
    user_id:     str
    platform:    str
    token:       str
    device_name: Optional[str]
    is_active:   bool
    created_at:  datetime
    updated_at:  datetime

    model_config = {"from_attributes": True}


# ── Send Notification ──────────────────────────────────────────────────────────

class SendNotificationRequest(BaseModel):
    user_id:     str  = Field(..., description="Target user ID")
    title:       str  = Field(..., description="Notification title")
    message:     str  = Field(..., description="Notification body text")
    screen_name: str  = Field(..., description="Screen to open on tap, e.g. OrderDetail")
    data:        Optional[Dict[str, Any]] = Field(
        default=None,
        description="Extra navigation data, e.g. {order_id: '123'}"
    )


class SendNotificationResult(BaseModel):
    token:   str
    status:  str   # sent | failed
    error:   Optional[str] = None


class SendNotificationResponse(BaseModel):
    user_id:  str
    total:    int
    sent:     int
    failed:   int
    results:  List[SendNotificationResult]


# ── Notification Logs ──────────────────────────────────────────────────────────

class NotificationLogOut(BaseModel):
    id:            UUID
    user_id:       str
    title:         str
    message:       str
    screen_name:   str
    data:          Optional[Dict[str, Any]]
    token:         str
    status:        str
    error_message: Optional[str]
    sent_at:       datetime

    model_config = {"from_attributes": True}


class NotificationLogsResponse(BaseModel):
    total:  int
    logs:   List[NotificationLogOut]


# ── Health ─────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status:   str
    database: str
    firebase: str


# ── Users ──────────────────────────────────────────────────────────────────────

class UserCreateRequest(BaseModel):
    user_id: str  = Field(..., description="Unique user identifier, e.g. user_42")
    name:    str  = Field(..., description="Display name, e.g. John Doe")


class UserOut(BaseModel):
    id:         UUID
    user_id:    str
    name:       str
    created_at: datetime

    model_config = {"from_attributes": True}


class UsersListResponse(BaseModel):
    total: int
    users: List[UserOut]
