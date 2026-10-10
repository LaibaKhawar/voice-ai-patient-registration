"""Call log, dashboard stats, auth and health endpoints."""

import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.auth import (
    SESSION_COOKIE,
    SESSION_MAX_AGE,
    api_key_is_valid,
    issue_session_token,
    require_admin,
)
from app.config import get_settings
from app.db import get_db
from app.envelope import APIError, ok
from app.models import CallSession
from app.schemas import CallDetailOut, CallOut, LoginRequest
from app.services.patients import registration_stats

calls_router = APIRouter(prefix="/calls", tags=["calls"], dependencies=[Depends(require_admin)])
stats_router = APIRouter(prefix="/stats", tags=["stats"], dependencies=[Depends(require_admin)])
auth_router = APIRouter(prefix="/auth", tags=["auth"])
health_router = APIRouter(tags=["health"])


@calls_router.get("", summary="List calls handled by the voice agent")
def list_calls(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    total = db.scalar(select(func.count()).select_from(CallSession)) or 0
    rows = db.scalars(
        select(CallSession).order_by(CallSession.created_at.desc()).limit(limit).offset(offset)
    ).all()
    data = [CallOut.model_validate(c).model_copy(update={"has_transcript": bool(c.transcript)})
            for c in rows]
    return ok(data, meta={"total": total, "limit": limit, "offset": offset})


@calls_router.get("/{call_id}", summary="Call detail including transcript")
def get_call(call_id: str, db: Session = Depends(get_db)):
    try:
        cid = uuid.UUID(call_id)
    except ValueError:
        raise APIError(400, "INVALID_ID", "call id must be a valid UUID.")
    call = db.get(CallSession, cid)
    if call is None:
        raise APIError(404, "NOT_FOUND", "Call not found.")
    out = CallDetailOut.model_validate(call).model_copy(update={"has_transcript": bool(call.transcript)})
    return ok(out)


@stats_router.get("", summary="Registration and call statistics")
def stats(db: Session = Depends(get_db)):
    return ok(registration_stats(db))


@auth_router.post("/login", summary="Exchange the API key for a dashboard session cookie")
def login(body: LoginRequest, response: Response):
    if not api_key_is_valid(body.api_key):
        raise APIError(401, "UNAUTHORIZED", "Invalid access key.")
    resp = ok({"authenticated": True})
    resp.set_cookie(
        SESSION_COOKIE, issue_session_token(), max_age=SESSION_MAX_AGE, httponly=True,
        secure=get_settings().is_production, samesite="strict", path="/",
    )
    return resp


@auth_router.post("/logout", summary="Clear the dashboard session")
def logout():
    resp = ok({"authenticated": False})
    resp.delete_cookie(SESSION_COOKIE, path="/")
    return resp


@auth_router.get("/session", summary="Check whether the caller is authenticated",
                 dependencies=[Depends(require_admin)])
def session():
    return ok({"authenticated": True})


@health_router.get("/health", summary="Liveness probe")
def health():
    return ok({"status": "ok"})


@health_router.get("/ready", summary="Readiness probe (checks the database)")
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise APIError(503, "NOT_READY", "Database is unavailable.")
    return ok({"status": "ready", "database": "ok"})
