"""
models/orm_models.py
SQLAlchemy ORM table definitions that mirror the SQL migration.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from db.database import Base


def _now():
    return datetime.now(timezone.utc)


class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id     = Column(String, nullable=False, index=True)
    platform    = Column(String, nullable=False, default="web")
    token       = Column(Text, nullable=False, unique=True)
    device_name = Column(String, nullable=True)
    is_active   = Column(Boolean, nullable=False, default=True)
    created_at  = Column(DateTime(timezone=True), default=_now)
    updated_at  = Column(DateTime(timezone=True), default=_now, onupdate=_now)


class User(Base):
    __tablename__ = "users"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(String, nullable=False, unique=True, index=True)
    name       = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id       = Column(String, nullable=False, index=True)
    title         = Column(Text, nullable=False)
    message       = Column(Text, nullable=False)
    screen_name   = Column(String, nullable=False)
    data          = Column(JSONB, nullable=True)
    token         = Column(Text, nullable=False)
    status        = Column(String, nullable=False, default="pending")  # sent | failed
    error_message = Column(Text, nullable=True)
    sent_at       = Column(DateTime(timezone=True), default=_now)
