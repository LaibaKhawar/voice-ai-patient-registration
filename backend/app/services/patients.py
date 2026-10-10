"""Patient service layer: the only code that reads or writes the patients table.

Both the REST API and the voice-agent tools call these functions, so
persistence behavior (idempotency, soft deletes, filtering) is identical no
matter how a record arrives.
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import CallSession, Patient
from app.schemas import PatientCreate, PatientUpdate

SORTABLE = {
    "created_at": Patient.created_at,
    "updated_at": Patient.updated_at,
    "last_name": func.lower(Patient.last_name),
    "first_name": func.lower(Patient.first_name),
    "date_of_birth": Patient.date_of_birth,
}


def _live():
    return Patient.deleted_at.is_(None)


def create_patient(
    db: Session, payload: PatientCreate, idempotency_key: str | None = None
) -> tuple[Patient, bool]:
    """Insert a patient. Returns (patient, created).

    If idempotency_key was already used, the original record is returned with
    created=False instead of inserting a duplicate.
    """
    if idempotency_key:
        existing = db.scalar(select(Patient).where(Patient.idempotency_key == idempotency_key))
        if existing:
            return existing, False

    data = payload.model_dump()
    if data.get("preferred_language") is None:
        data["preferred_language"] = "English"
    patient = Patient(**data, idempotency_key=idempotency_key)
    db.add(patient)
    try:
        db.commit()
    except IntegrityError:
        # A concurrent request with the same key won the race.
        db.rollback()
        if idempotency_key:
            existing = db.scalar(select(Patient).where(Patient.idempotency_key == idempotency_key))
            if existing:
                return existing, False
        raise
    db.refresh(patient)
    return patient, True


def get_patient(db: Session, patient_id: uuid.UUID, include_deleted: bool = False) -> Patient | None:
    stmt = select(Patient).where(Patient.patient_id == patient_id)
    if not include_deleted:
        stmt = stmt.where(_live())
    return db.scalar(stmt)


def list_patients(
    db: Session,
    *,
    last_name: str | None = None,
    date_of_birth: date | None = None,
    phone_number: str | None = None,
    q: str | None = None,
    sort: str = "created_at",
    order: str = "desc",
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Patient], int]:
    filters: list[Any] = [_live()]
    if last_name:
        filters.append(func.lower(Patient.last_name) == last_name.strip().lower())
    if date_of_birth:
        filters.append(Patient.date_of_birth == date_of_birth)
    if phone_number:
        filters.append(Patient.phone_number == phone_number)
    if q:
        term = f"%{q.strip().lower()}%"
        digits = "".join(ch for ch in q if ch.isdigit())
        clauses = [
            func.lower(Patient.first_name).like(term),
            func.lower(Patient.last_name).like(term),
            func.lower(func.concat(Patient.first_name, " ", Patient.last_name)).like(term),
            func.lower(Patient.email).like(term),
        ]
        if digits:
            clauses.append(Patient.phone_number.like(f"%{digits}%"))
        filters.append(or_(*clauses))

    total = db.scalar(select(func.count()).select_from(Patient).where(*filters)) or 0
    sort_col = SORTABLE[sort]
    sort_expr = sort_col.desc() if order == "desc" else sort_col.asc()
    rows = db.scalars(
        select(Patient).where(*filters).order_by(sort_expr, Patient.patient_id).limit(limit).offset(offset)
    ).all()
    return list(rows), total


def update_patient(db: Session, patient: Patient, payload: PatientUpdate) -> Patient:
    for field in payload.model_fields_set:
        value = getattr(payload, field)
        if field == "preferred_language" and value is None:
            value = "English"
        setattr(patient, field, value)
    patient.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(patient)
    return patient


def soft_delete_patient(db: Session, patient: Patient) -> Patient:
    now = datetime.now(timezone.utc)
    patient.deleted_at = now
    patient.updated_at = now
    db.commit()
    db.refresh(patient)
    return patient


def find_live_by_phone(db: Session, phone_number: str) -> Patient | None:
    """Most recently created live patient with this phone number, if any."""
    return db.scalar(
        select(Patient)
        .where(_live(), Patient.phone_number == phone_number)
        .order_by(Patient.created_at.desc())
        .limit(1)
    )


def registration_stats(db: Session, days: int = 14) -> dict[str, Any]:
    """Aggregate counts for the dashboard overview. All values come from the DB."""
    now = datetime.now(timezone.utc)
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    window_start = start_of_today - timedelta(days=days - 1)

    total = db.scalar(select(func.count()).select_from(Patient).where(_live())) or 0
    today = db.scalar(
        select(func.count()).select_from(Patient).where(_live(), Patient.created_at >= start_of_today)
    ) or 0
    day_col = func.date_trunc("day", func.timezone("UTC", Patient.created_at))
    per_day_rows = db.execute(
        select(day_col.label("day"), func.count())
        .where(_live(), Patient.created_at >= window_start)
        .group_by("day")
    ).all()
    per_day = {row[0].date().isoformat(): row[1] for row in per_day_rows}
    series = [
        {"date": (window_start + timedelta(days=i)).date().isoformat(),
         "count": per_day.get((window_start + timedelta(days=i)).date().isoformat(), 0)}
        for i in range(days)
    ]

    outcome_rows = db.execute(
        select(func.coalesce(CallSession.outcome, CallSession.state), func.count()).group_by(
            func.coalesce(CallSession.outcome, CallSession.state)
        )
    ).all()
    calls_by_outcome = {row[0]: row[1] for row in outcome_rows}

    return {
        "total_patients": total,
        "registered_today": today,
        "registrations_by_day": series,
        "total_calls": sum(calls_by_outcome.values()),
        "calls_by_outcome": calls_by_outcome,
        "generated_at": now.isoformat(),
    }
