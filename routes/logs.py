"""
routes/logs.py
Endpoints for querying notification delivery logs.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.database import get_db
from models.orm_models import NotificationLog
from models.schemas import NotificationLogOut, NotificationLogsResponse

router = APIRouter(prefix="/logs", tags=["Logs"])


# ── GET /logs ──────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=NotificationLogsResponse,
    summary="Query notification delivery logs",
)
def get_logs(
    user_id: Optional[str] = Query(default=None, description="Filter by user ID"),
    status:  Optional[str] = Query(default=None, description="Filter by status: sent | failed"),
    limit:   int            = Query(default=50,  ge=1, le=200, description="Max records to return"),
    offset:  int            = Query(default=0,   ge=0,         description="Pagination offset"),
    db: Session = Depends(get_db),
):
    """
    Returns notification logs, optionally filtered by `user_id` and/or
    `status`. Results are ordered newest-first.
    """
    query = db.query(NotificationLog)

    if user_id:
        query = query.filter(NotificationLog.user_id == user_id)
    if status:
        query = query.filter(NotificationLog.status == status)

    total = query.count()
    logs  = (
        query
        .order_by(NotificationLog.sent_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return NotificationLogsResponse(total=total, logs=logs)


# ── GET /logs/{user_id} ────────────────────────────────────────────────────────

@router.get(
    "/{user_id}",
    response_model=NotificationLogsResponse,
    summary="Get logs for a specific user",
)
def get_user_logs(
    user_id: str,
    status:  Optional[str] = Query(default=None, description="sent | failed"),
    limit:   int            = Query(default=20, ge=1, le=100),
    offset:  int            = Query(default=0,  ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(NotificationLog).filter(NotificationLog.user_id == user_id)

    if status:
        query = query.filter(NotificationLog.status == status)

    total = query.count()
    logs  = (
        query
        .order_by(NotificationLog.sent_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return NotificationLogsResponse(total=total, logs=logs)
